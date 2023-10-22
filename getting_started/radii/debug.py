import os
import sys
import SimpleITK as sitk
import cv2
import matplotlib.pyplot as plt

nb_dir = os.path.split(os.getcwd())[0]
if (nb_dir not in sys.path):
    sys.path.append(nb_dir)

import radii as radi

amDataPath = str('../data/am/')
tifDataPath = str('../data/tif/')
dnsTifDataPath = str('../data/dnsTif/')
amOutputPath = str('../output/am/')

s13_data = amDataPath + 'S13_final_done_Alison_zScale_40.am'
debug_s13_data = amDataPath + 'debug-S13_final_done_Alison_zScale_40.am'

s13_r = amOutputPath + 's13-r.am'
debug_s13_r = amOutputPath + 'debug-s13-r.am'
s13_points = radi.spacialGraph.getSpatialGraphPoints(s13_data)

s13_points = list([[int(y / 0.092) for y in x] for x in s13_points])

s13_tif = tifDataPath + 'S13_max_z_projection.tif'

imageFileReader = sitk.ImageFileReader()
imageFileReader.SetFileName(s13_tif)
s13_image = imageFileReader.Execute()
# s13_image_for_denoising = cv2.imread(s13_tif)
# denoised_s13_image = cv2.fastNlMeansDenoising(s13_image_for_denoising, None, 3, 7, 21)
# cv2.imwrite( '../data/dnsTif/s13_dns.tif', denoised_s13_image)

# s13_dns_tif = dnsTifDataPath + 's13_dns.tif'
# imageFileReader.SetFileName(s13_dns_tif)
# s13_dns_image = imageFileReader.Execute()

# print("point id 306: ")
# res = radi.radius.getHalfMaxRadiusAtThisPoint(s13_image, s13_points[306])
# print(res[0], res[1], res[2])
# print(s13_image)
# print("denoised, point id 306: ")
# print(s13_dns_image)
# res = radi.radius.getHalfMaxRadiusAtThisPoint(s13_image, s13_points)
res = radi.radius.getRadiiHalfMax(s13_image, s13_points)

# print("point id 307: ")
# res = radi.radius.getHalfMaxRadiusAtThisPoint(s13_image, s13_points[307])
# print(res[0], res[1], res[2])

# # print("denoised, point id 307: ")
# # res = radi.radius.getHalfMaxRadiusAtThisPoint(s13_dns_image, s13_points[307])
# # print(res[0], res[1], res[2])

# print("point id 308: ")
# res = radi.radius.getHalfMaxRadiusAtThisPoint(s13_image, s13_points[308])
# print(res[0], res[1], res[2])

# print("denoised, point id 308: ")
# res = radi.radius.getHalfMaxRadiusAtThisPoint(s13_dns_image, s13_points[308])
# print(res[0], res[1], res[2])

radii = res[1]
radii = [r * 0.092 for r in radii]
radi.spacialGraph.write_spacial_graph_with_thickness(s13_data, s13_r, radii)
