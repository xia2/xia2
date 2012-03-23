import copy

def ward_cluster(data, distances = None):
    '''Another go at ward clustering. Much of this depends on the fact that we
    merge downwards.'''

    n_data = len(data)
    clusters = [[j] for j in range(n_data)]
    indices = [j for j in range(len(clusters))]

    history = []

    # if we have not already been given computed distances, compute them,
    # based on common sense...

    if not distances:
        distances = { }
        for i in range(n_data - 1):
            for j in range(i + 1, n_data):
                try:
                    distance = sum([(di - dj) * (di - dj) for \
                                    di, dj in zip(data[i], data[j])])
                except TypeError, e:
                    distance = (data[i] - data[j]) * (data[i] - data[j])

                distances[(i, j)] = distance / 2

    while len(clusters) > 1:
        
        # compute nearest neighbours

        neighbour = { }

        for i in range(len(clusters) - 1):

            dmin = 1.0e100

            for j in range(i + 1, len(clusters)):
                if distances[(indices[i], indices[j])] >= dmin:
                    continue
                dmin = distances[(indices[i], indices[j])]
                neighbour[i] = dmin, j

        # find nearest of near neighbours, i.e. the target to merge the source
        # into

        dmin = 1.0e100
        target = None
        source = None

        for i in range(len(clusters) - 1):
            if neighbour[i][0] >= dmin:
                continue

            dmin = neighbour[i][0]
            target = i
            source = neighbour[i][1]

        # perform the merge

        source_cluster = clusters.pop(source)
        source_index = indices.pop(source)
        history.append((copy.deepcopy(clusters[target]), source_cluster, dmin))

        # update distances

        for i in range(len(clusters)):
            if i == target:
                continue
            
            n_tot = len(clusters[target]) + len(source_cluster) + \
                len(clusters[i])

            if indices[i] < indices[target]:
                d_target = distances[(indices[i], indices[target])]
            else:
                d_target = distances[(indices[target], indices[i])]

            if indices[i] < source_index:
                d_source = distances[(indices[i], source_index)]
            else:
                d_source = distances[(source_index, indices[i])]

            index_low, index_high = min(indices[i], indices[target]), \
                max(indices[i], indices[target])

            distances[(index_low, index_high)] = (
                (len(clusters[i]) + len(clusters[target])) * d_target +
                (len(clusters[i]) + len(source_cluster)) * d_source -
                len(clusters[i]) * dmin) / float(n_tot)

        # delete the source related distances

        for index in sorted(distances):
            if source_index in index:
                del(distances[index])

        clusters[target] += source_cluster

    return history

if __name__ == '__main__':

    data = [2.0, 6.1, 5.1, 6.2, 2.2, 2.3, 2.4, 0.1, 0.2, 0.3]

    history = ward_cluster(data)

    for i, j, d in history:
        print '%.2f' % d, [data[_i] for _i in i], [data[_j] for _j in j]
