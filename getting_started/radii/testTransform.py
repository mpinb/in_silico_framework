import numpy as np


def solve_affine(p1, p2, p3, p4, s1, s2, s3, s4):
    x = np.transpose(np.matrix([p1, p2, p3, p4]))
    y = np.transpose(np.matrix([s1, s2, s3, s4]))
    # add ones on the bottom of x and y
    x = np.vstack((x, [1, 1, 1, 1]))
    y = np.vstack((y, [1, 1, 1, 1]))
    # solve for A2
    A2 = y * x.I
    # return function that takes input x and transforms it
    # don't need to return the 4th row as it is
    return lambda x: (A2 * np.vstack((np.matrix(x).reshape(3, 1), 1)))[0:3, :]


primary_system1 = np.array([187.881546, -54.137070, 1038.130005])
primary_system2 = np.array([181.608002, 519.708008, 21.600000])
primary_system3 = np.array([9.349396, 8.509659, 1012.554993])
primary_system4 = np.array([376.924011, 351.992004, 2.800000])

secondary_system1 = np.array([-6274.850000, -5583.000000, -245.260000])
secondary_system2 = np.array([-5701.480000, -5553.070000, 1024.910000])
secondary_system3 = np.array([-6201.160000, -5757.260000, -213.290000])
secondary_system4 = np.array([-5881.270000, -5368.640000, 1048.410000])

transformFn = solve_affine(primary_system1, primary_system2, primary_system3,
                           primary_system4, secondary_system1,
                           secondary_system2, secondary_system3,
                           secondary_system4)

# test: transform primary_system1 and we should get secondary_system1
M = np.matrix(secondary_system1).T - transformFn(primary_system1)
# M = np.matrix(secondary_system2).T - transformFn( primary_system1 )
print(M)
print((np.matrix(secondary_system1).T))
# np.linalg.norm of above is 0.02555

# transform another point (x,y,z).
# transformed = transformFn((x,y,z))
