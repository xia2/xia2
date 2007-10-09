import math

def celldiff(a, b):

    angles = 0.0
    lengths = 0.0
    
    for j in range(3):

        lengths += math.fabs(a[j] - b[j])
        angles += math.fabs(a[j + 3] - b[j + 3])

    return lengths / 3, angles / 3







if __name__ == '__main__':

    cella = 51.73, 51.85, 158.13, 90.00, 90.05, 90.20
    cellb = 51.72, 51.72, 158.25, 90.00, 90.00, 90.00

    print '%.2f %.2f' % celldiff(cella, cellb)

    
    
