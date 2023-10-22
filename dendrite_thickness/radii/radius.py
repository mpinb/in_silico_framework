import SimpleITK as sitk
import numpy as np
from scipy.stats import norm
from scipy.optimize import curve_fit

XY_RESOLUTION = 0.092
Z_RESOLUTION = 0.5
XY_SIZE = 20
Z_SIZE = 4
PROX_IM_SIZE = 20
XY_SIZE_PIXELS = XY_SIZE / XY_RESOLUTION
Z_SIZE_PIXELS = Z_SIZE / Z_RESOLUTION

# Ray burst settings
NUM_RAYS = 36  # per 1 degrees
RAY_LEN_PER_DIRECTION = XY_SIZE / 2.0  # microns
RAY_LEN_PER_DIRECTION_IMAGE_COORDS = RAY_LEN_PER_DIRECTION / XY_RESOLUTION


def getEuclideanDistance(x, y):
    return np.sqrt((x[0] - y[0])**2 + (x[1] - y[1])**2)


def getRadiiHalfMax(
    image,
    pts,
):

    halfmaxvalues = []
    min_radii = []
    avg_radii = []
    front_contour = []
    back_contour = []
    rayimages = []
    minrayimages = []
    mincontptimages = []
    frontvaluesgrandlist = []
    backvaluesgrandlist = []
    fronthalfmaxgrandlist = []
    backhalfmaxgrandlist = []

    for pt in pts:
        # Send rays every 10 degrees and find the min and avg radius
        [
            halfmaxvalue, min_radius, avg_radius, front_contour_pt,
            back_contour_pt, rayim, minrayim, mincontptim, frontvalues,
            backvalues, front_contour_pts, back_contour_pts
        ] = getHalfMaxRadiusAtThisPoint(image, pt)
        halfmaxvalues.append(halfmaxvalue)
        min_radii.append(min_radius)
        avg_radii.append(avg_radius)
        front_contour.append(front_contour_pt)
        back_contour.append(back_contour_pt)
        rayimages.append(rayim)
        minrayimages.append(minrayim)
        mincontptimages.append(mincontptim)
        frontvaluesgrandlist.append(frontvalues)
        backvaluesgrandlist.append(backvalues)
        fronthalfmaxgrandlist.append(front_contour_pts)
        backhalfmaxgrandlist.append(back_contour_pts)

    return [
        halfmaxvalues, min_radii, avg_radii, front_contour, back_contour,
        rayimages, minrayimages, mincontptimages, frontvaluesgrandlist,
        backvaluesgrandlist, fronthalfmaxgrandlist, backhalfmaxgrandlist
    ]


def getHalfMaxRadiusAtThisPoint(im, pt):

    # Radius list
    tmpim_rays = im  #sitk.Image()
    tmpim_minray = im  #sitk.Image()
    tmpim_mincontpts = im  #sitk.Image()
    #tmpim = sitk.Or(tmpim,im)
    fronthalfmaxptlist = []
    backhalfmaxptlist = []
    rad_list = []
    lineprof_front_list = []
    lineprof_back_list = []
    frontvalueslist = []
    backvalueslist = []

    for j in range(NUM_RAYS):
        phi = j * (np.pi / NUM_RAYS)

        # collect the
        linear_profile_front = getLineProfileIndices(
            pt, phi, im, RAY_LEN_PER_DIRECTION_IMAGE_COORDS, front=True)
        linear_profile_back = getLineProfileIndices(
            pt, phi, im, RAY_LEN_PER_DIRECTION_IMAGE_COORDS, front=False)

        if len(linear_profile_front) > 5 and len(linear_profile_back) > 5:
            lineprof_front_list.append(linear_profile_front)
            lineprof_back_list.append(linear_profile_back)
            [fronthalfmaxpt,
             front_profile_values] = getHalfMaxPoint(im, linear_profile_front,
                                                     pt)
            [backhalfmaxpt,
             back_profile_values] = getHalfMaxPoint(im, linear_profile_back, pt)

            # for debug
            frontvalueslist.append(front_profile_values)
            backvalueslist.append(back_profile_values)

            fronthalfmaxptlist.append(fronthalfmaxpt)
            backhalfmaxptlist.append(backhalfmaxpt)

            # find the radius
            radius = getEuclideanDistance(fronthalfmaxpt, backhalfmaxpt)
            rad_list.append(radius)

            ##tmpim_rays = sitk.Or(tmpim_rays,convertPointsToImage(linear_profile_front, im))
            ##tmpim_rays = sitk.Or(tmpim_rays,convertPointsToImage(linear_profile_back, im))

        else:
            rad_list.append(100)
            fronthalfmaxptlist.append(pt)
            backhalfmaxptlist.append(pt)
            lineprof_front_list.append(pt)
            lineprof_back_list.append(pt)
            #print pt

    min_ind = np.argmin(np.array(rad_list))

    #display the shortest ray
    ##tmpim_minray = sitk.Or(tmpim_minray,convertPointsToImage(lineprof_front_list[min_ind], im))
    ##tmpim_minray = sitk.Or(tmpim_minray,convertPointsToImage(lineprof_back_list[min_ind], im))

    #display contour pts
    ##tmpim_mincontpts = sitk.Or(tmpim_mincontpts,convertPointsToImage(fronthalfmaxptlist[min_ind], im))
    ##tmpim_mincontpts = sitk.Or(tmpim_mincontpts,convertPointsToImage(backhalfmaxptlist[min_ind], im))

    halfmaxvalue = im.GetPixel([pt[0], pt[1], 0]) / 2.0
    return [
        halfmaxvalue,
        np.min(np.array(rad_list)),
        np.mean(np.array(rad_list)), fronthalfmaxptlist[min_ind],
        backhalfmaxptlist[min_ind], tmpim_rays, tmpim_minray, tmpim_mincontpts,
        frontvalueslist, backvalueslist, fronthalfmaxptlist, backhalfmaxptlist
    ]


def gaus(x, a, x0, sigma):
    return a * exp(-(x - x0)**2 / (2 * sigma**2))


def getHalfMaxPoint2(image, linear_profile, centerpt):
    n = len(linear_profile)
    x = np.array(linear_profile)

    pixel_values = []
    for i in range(len(linear_profile)):
        pixelvalue = image.GetPixel(linear_profile[i])
        pixel_values.append(pixelvalue)

    y = np.array(pixel_values)

    mean = sum(x * y) / n
    sigma = sum(y * (x - mean)**2) / n

    popt, pcov = curve_fit(gaus, x, y, p0=[1, mean, sigma])
    print(popt)
    # parameters = norm.fit(pixel_values)
    # for i in raneg(len(linear_profile)):
    #     if (pixel_values[i])
    contour_pt = 10
    pixel_value_list = pixel_values
    return contour_pt, pixel_value_list


def getHalfMaxPoint(image, linear_profile, centerpt):
    centerpixelvalue = image.GetPixel([centerpt[0], centerpt[1], 0])

    # print("-----------------------------------")
    # orig_centerpixelvalue = image.GetPixel(centerpt)
    # print("value of original center point")
    # print(orig_centerpixelvalue)

    # centerpt_new = getMaxfromLineProfile(linear_profile, image)
    # new_centerpixelvalue = image.GetPixel(centerpt_new)
    # print("value of new center point")
    # print(new_centerpixelvalue)
    # print("-----------------------------------")

    # if (new_centerpixelvalue >= 10.0 * orig_centerpixelvalue):
    #     centerpixelvalue = new_centerpixelvalue
    #     contour_pt = centerpt_new
    # else:
    #     centerpixelvalue = orig_centerpixelvalue
    #     contour_pt = centerpt

    # uncomment the below two lines to get the old result from the radii
    # centerpixelvalue = orig_centerpixelvalue
    # contour_pt = centerpt

    pixel_value_list = []
    # image linear_profile
    contour_pt = centerpt
    if centerpixelvalue < 50:
        return centerpt, pixel_value_list

    for i in range(len(linear_profile) - 1):
        pixelvalue1 = image.GetPixel(linear_profile[i])
        pixelvalue2 = image.GetPixel(linear_profile[i + 1])
        pixel_value_list.append(pixelvalue1)
        if pixelvalue1 >= centerpixelvalue / 2.0 and pixelvalue2 <= centerpixelvalue / 2.0:
            contour_pt = linear_profile[i]
            break

    return contour_pt, pixel_value_list


def getMaxfromLineProfile(linear_profile, image):
    values = []
    for i in range(len(linear_profile)):
        values.append(image.GetPixel(linear_profile[i]))
        indexOfMaxValue = np.argmax(np.array(values))
    return linear_profile[indexOfMaxValue]


def getMinFromLineProfile(linear_profile, image):
    values = []
    for i in range(len(linear_profile)):
        #values.append(image.GetPixel([linear_profile[i][0],linear_profile[i][1],0]))
        values.append(image.GetPixel(linear_profile[i]))
    return linear_profile[np.argmin(np.array(values))]


# In[9]:


def getLineProfileIndices(pt,
                          phi,
                          image_plane,
                          RAY_LEN_PER_DIRECTION_IMAGE_COORDS,
                          front=True):
    profile_indices = []
    #profile_values = []

    x0 = pt[0]
    y0 = pt[1]

    x_f = x0
    y_f = y0
    for k in range(int(RAY_LEN_PER_DIRECTION_IMAGE_COORDS)):
        if front:
            x_f = x_f + 1
        else:
            x_f = x_f - 1

        y_f = y_f - y0
        x_f = x_f - x0

        y_new = int(y_f * np.cos(phi) - x_f * np.sin(phi))
        x_new = int(y_f * np.sin(phi) + x_f * np.cos(phi))

        y_new = y_new + y0
        x_new = x_new + x0

        y_f = y_f + y0
        x_f = x_f + x0

        if (x_new <= 1 or y_new <= 1 or x_new >= image_plane.GetWidth() or
                y_new >= image_plane.GetHeight()):
            #print x_new,y_new
            break

        else:
            profile_indices.append([x_new, y_new])
            #profile_values.append()
    #print  profile_indices
    return profile_indices
