# -*- coding: utf-8 -*-
"""
Compute Single-Shot K-Means with LLoyd's Algorithm or Gradient Descent

Algorithm Flow -
    1: On each site, initialize Random Centroids
    2: On each site, compute a clustering with k-many clusters
    [lloyd's algorithm]
        3: On each site, compute a local mean for each cluster
        4: On each site, recompute centroids as equal to local means
    [gradient descent]
        3: On each site, compute a local gradient for each cluster
        4: On each site, update centroids via gradient descent
    5: On each site,
        if change in centroids below some epsilon, STOP, report STOPPED
        else GOTO step 3
    6: On each site, broadcast local centroids to aggregator
    7: On the aggregator, compute merging of clusters according to
        least merging error (e.g. smallest distance betweeen centroids)
    8: Broadcast merged centroids to all sites
"""

import logging

import dkmeans.local_computations as local
import dkmeans.remote_computations as remote
from dkmeans.data import get_data_dims, split_over_nodes, get_dataset


DEFAULT_optimization = 'lloyd'
DEFAULT_sites = 2
DEFAULT_epsilon = 0.00001
DEFAULT_shuffle = True
DEFAULT_lr = 0.01
DEFAULT_verbose = True

logger = logging.getLogger('dkmeans')
logger.setLevel(logging.INFO)


def main(X, k, optimization=DEFAULT_optimization, s=DEFAULT_sites,
         epsilon=DEFAULT_epsilon, shuffle=DEFAULT_shuffle, lr=DEFAULT_lr,
         verbose=DEFAULT_verbose):
    """
        Local Variables - X: a list of N many m x n matrices storing data
                          k: number of clusters (int)
                          local_centroids : a s x k 2-d list of
                          m x n matrices storing cluster centroids
    """
    m, n = get_data_dims(X)
    nodes, inds = split_over_nodes(X, s, shuffle=shuffle)
    X = [X[i] for i in inds]  # Reshuffle x to match the random
    tracked_delta = []
    num_iter = 0
    not_converged = True

    # Have each site compute k initial clusters locally
    local_centroids = [local.initialize_own_centroids(node, k)
                       for node in nodes]

    # Local Optimization Loop
    while not_converged:
        cluster_labels = [None for j in range(s)]  # the clusterings
        local_delta = [None for j in range(s)]  # Track all local delta
        local_stop = [False for j in range(s)]  # And all local stopping conds
        for i, node in enumerate(nodes):
            # Each local site computes its cluster
            cluster_labels[i] = \
                         local.compute_clustering(node, local_centroids[i])
            if optimization == 'lloyd':
                # Computes its local mean if doing lloyd, and updates centroids
                local_means = local.compute_mean(node,
                                                 cluster_labels[i], k)
                previous_centroids = local_centroids[i][:]
                local_centroids[i] = local_means
            elif optimization == 'gradient':
                # Computes the local gradient if doing GD, and takes a GD step
                local_grad = local.compute_gradient(node,
                                                    cluster_labels[i],
                                                    local_centroids[i],
                                                    lr)
                [local_centroids[i], previous_centroids] = \
                    local.gradient_step(local_grad, local_centroids[i])
            # Check local stopping conditions
            local_stop[i], local_delta[i] = \
                local.check_stopping(local_centroids[i],
                                     previous_centroids, epsilon)
        num_iter += 1
        tracked_delta.append(local_delta)
        if verbose:
            logger.info("Single-Shot %s ; iter : %d delta : %f"
                        % (optimization, num_iter, max(local_delta)))

        # if any of the sites are still iterating, keep the global loop running
        # TODO: we can save computations by locally waiting if local
        #       conditions are met
        not_converged = any(local_stop)

    # Aggregate clusters remotely
    remote_centroids = remote.aggregate_clusters(local_centroids)
    # And compute the final global clustering
    cluster_labels = [clusters for node in nodes for clusters in
                      local.compute_clustering(node, remote_centroids)]
    return {'centroids': remote_centroids, 'cluster_labels': cluster_labels,
            'X': X, 'delta': tracked_delta, 'iter': num_iter,
            'name': 'singleshot_%s' % optimization}


if __name__ == '__main__':
    result = main(get_dataset(100, theta=[[-1, 0.1], [1, 0.1]], m=1, n=2), 2)
