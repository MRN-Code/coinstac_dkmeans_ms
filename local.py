import os
import sys
import logging
import numpy as np
import utils as ut
import configparser
from . import local_computations as local

CONFIG_FILE = 'dkm_config.cfg'
DEFAULT_data_file = 'data.txt'
DEFAULT_k = 5
DEFAULT_shuffle = True
DEFAULT_learning_rate = 0.001
DEFAULT_optimization = 'lloyd'


def dkm_local_noop(args, **kwargs):
    """
        # Description:
            Nooperation

        # PREVIOUS PHASE:
            NA

        # INPUT:

        # OUTPUT:

        # NEXT PHASE:
            remote_init_env
    """
    computation_output = dict(output=dict(computation_phase="dkm_local_noop"),
                              )
    return computation_output


def dkm_local_init_env(args,
                       config_file=CONFIG_FILE,
                       k=DEFAULT_k,
                       optimization=DEFAULT_optimization,
                       shuffle=DEFAULT_shuffle,
                       learning_rate=DEFAULT_learning_rate,
                       **kwargs):
    """
        # Description:
            Initialize the local environment, creating the config file.

        # PREVIOUS PHASE:
            remote_init_env

        # INPUT:

            |   name            |   type    |   default     |
            |   ---             |   ---     |   ---         |
            |   config_file     |   str     |   config.cfg  |
            |   k               |   int     |   5           |
            |   optimization    |   str     |   lloyd       |
            |   shuffle         |   bool    |   False       |
            |   data_file       |   str     |   data.txt    |
            |   learning_rate   |   float   |   0.001       |

        # OUTPUT:
            - config file written to disk

        # NEXT PHASE:
            local_init_centroids
    """
    state = args['state']
    inputs = args['input']
    data_file = inputs['all_windows']
    ut.log('LOCAL: Initializing remote environment', state)
    config_path = os.path.join(state['outputDirectory'], config_file)
    if not os.path.exists(config_path):
        config = configparser.ConfigParser()
        config['LOCAL'] = dict(k=k,
                               optimization=optimization,
                               shuffle=shuffle,
                               data_file=data_file,
                               learning_rate=learning_rate)
        with open(config_path, 'w') as file:
            config.write(file)
    # output
    computation_output = dict(
        output=dict(
            config_file=config_path,
            computation_phase="dkm_local_init_env"),
        state=state
    )
    return computation_output


def dkm_local_init_centroids(args, **kwargs):
    """
        # Description:
            Initialize K centroids from own data.

        # PREVIOUS PHASE:
            local_init_env

        # INPUT:

            |   name             |   type    |   default     |
            |   ---              |   ---     |   ---         |
            |   config_file      |   str     |   config.cfg  |

        # OUTPUT:
            - centroids: list of numpy arrays

        # NEXT PHASE:
            remote_init_centroids
    """
    state = args['state']
    inputs = args['input']
    config_file = inputs['config_file']
    ut.log('LOCAL: Initializing centroids', state)
    config = configparser.ConfigParser()
    config.read(config_file)
    data = np.load(config['LOCAL']['data_file'])
    centroids = local.initialize_own_centroids(data, config['LOCAL']['k'])
    # output
    computation_output = dict(output=dict(
        config_file=config_file,
        centroids=centroids,
        computation_phase="dkm_local_init_env"),
        state=state
    )
    return computation_output


def dkm_local_compute_clustering(args,
                                 **kwargs):
    """
        # Description:
            Assign data instances to clusters.

        # PREVIOUS PHASE:
            remote_init_centroids (on first run only)
            remote_cehck_convergence

        # INPUT:

            |   name                |   type    |   default     |
            |   ---                 |   ---     |   ---         |
            |   config_file         |   str     |   config.cfg  |
            |   remote_centroids    |   list    |   None        |
            |   computation_phase   |   list    |   None        |

        # OUTPUT:
            - centroids: list of numpy arrays

        # NEXT PHASE:
            remote_init_centroids
    """
    inputs = args['input']
    state = args['state']
    config_file = inputs['config_file']
    remote_centroids = inputs['remote_centroids']
    computation_phase = inputs['computation_phase']
    ut.log('LOCAL: computing clustering', state)
    if remote_centroids is None:
        raise ValueError(
            "LOCAL: at local_compute_clustering - remote_centroids not passed correctly"
        )
    if computation_phase is None:
        raise ValueError(
            "LOCAL: at local_compute_clustering - computation_phase not passed correctly"
        )
    config = configparser.ConfigParser()
    config.read(config_file)
    data = np.loadtxt(config['LOCAL']['data_file'])

    cluster_labels = local.compute_clustering(data, remote_centroids)

    new_comp_phase = "dkm_local_compute_clustering"
    if computation_phase == "dkm_remote_optimization_step":
        new_comp_phase = "dkm_local_compute_clustering_2"
    computation_output = dict(output=dict(
        computation_phase=new_comp_phase,
        cluster_labels=cluster_labels,
        remote_centroids=remote_centroids,
    ),
        state=state
    )
    return computation_output


def dkm_local_compute_optimizer(args,
                                **kwargs):
    """
        # Description:
            Compute local optimizers with local data.

        # PREVIOUS PHASE:
            local_compute_clustering

        # INPUT:

            |   name                |   type    |   default     |
            |   ---                 |   ---     |   ---         |
            |   config_file         |   str     |   config.cfg  |
            |   remote_centroids    |   list    |   None        |
            |   cluster_labels      |   list    |   None        |

        # OUTPUT:
            - centroids: list of numpy arrays

        # NEXT PHASE:
            remote_init_centroids
    """
    state = args['state']
    inputs = args['input']
    config_file = inputs['config_file']
    remote_centroids = inputs['remote_centroids']
    cluster_labels = inputs['cluster_labels']
    if remote_centroids is None:
        raise ValueError(
            "LOCAL: at local_compute_clustering - remote_centroids not passed correctly"
        )
    if cluster_labels is None:
        raise ValueError(
            "LOCAL: at local_compute_clustering - cluster_labels not passed correctly"
        )
    ut.log('LOCAL: computing optimizers', state)
    config = configparser.ConfigParser()
    config.read(config_file)
    data = np.loadtxt(config['LOCAL']['data_file'])
    k = config['LOCAL']['k']
    learning_rate = config['LOCAL']['learning_rate']
    optimization = config['LOCAL']['optimization']
    if optimization == 'lloyd':
        local_optimizer = local.compute_mean(data, cluster_labels, k)
    elif optimization == 'gradient':
        # Gradient descent has sites compute gradients locally
        local_optimizer = \
            local.compute_gradient(data, cluster_labels[i],
                                   remote_centroids, learning_rate)
    computation_output = dict(output=dict(
        local_optimizer=local_optimizer,
        computation_phase="dkm_local_compute_optimizer"),
        state=state
    )
    return computation_output


if __name__ == '__main__':

    parsed_args = json.loads(sys.stdin.read())
    phase_key = list(listRecursive(parsed_args, 'computation_phase'))
    if not phase_key:  # FIRST PHASE
        computation_output = local_noop(**parsed_args['input'])
        sys.stdout.write(computation_output)
    elif "remote_init_env" in phase_key:  # REMOTE -> LOCAL
        computation_output = local_init_env(**parsed_args['input'])
        computation_output = local_init_centroids(**computation_output)
        sys.stdout.write(computation_output)
    elif "remote_init_centroids" in phase_key:  # REMOTE -> LOCAL
        computation_output = local_compute_clustering(**parsed_args['input'])
        computation_output = local_compute_optimizer(**computation_output)
        sys.stdout.write(computation_output)
    elif "remote_optimization_step" in phase_key:  # REMOTE -> LOCAL
        computation_output = local_compute_clustering(**parsed_args['input'])
        sys.stdout.write(computation_output)
    elif 'remote_converged_false' in phase_key:  # REMOTE -> LOCAL
        computation_output = local_compute_optimizer(**parsed_args['input'])
        sys.stdout.write(computation_output)
    elif 'remote_aggregate_output' in phase_key:  # REMOTE -> LOCAL
        computation_output = local_compute_clustering(**parsed_args['input'])
    else:
        raise ValueError('Phase error occurred at LOCAL')
