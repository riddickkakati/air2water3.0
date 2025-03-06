import ee
import folium
import requests
from PIL import Image
from io import BytesIO
import numpy as np
import matplotlib.pyplot as plt
from django.conf import settings

def MNDWICalculator(green, SWIR1, NIR, red, blue, image):

    MNDWIimage = green.expression('(green-swir1)/(green+swir1)', {
        'green': green,
        'swir1': SWIR1
    })
    NDVIimage = NIR.expression('(NIR-red)/(NIR+red)', {
        'NIR': NIR,
        'red': red
    })
    EVIimage = NIR.expression('2.5 * (NIR - red) / (1 + NIR + 6 * red - 7.5 * blue)', {
        'NIR': NIR,
        'red': red,
        'blue': blue
    })
    water = (MNDWIimage.gt(NDVIimage).Or(MNDWIimage.gt(EVIimage))).And(EVIimage.lt(0.1))
    waterMasked = water.updateMask(water.gt(0))
    return image.mask(waterMasked)

def mapMNDWIlandsat(image):
    green = image.select(1)
    SWIR1 = image.select(4)
    NIR = image.select(3)
    red = image.select(2)
    blue = image.select(0)
    return MNDWICalculator(green, SWIR1, NIR, red, blue, image)


def mapMNDWIsentinel(image):
    green = image.select(1)
    SWIR1 = image.select(8)
    NIR = image.select(6)
    red = image.select(2)
    blue = image.select(0)
    return MNDWICalculator(green, SWIR1, NIR, red, blue, image)

def CIcalc(red, green):
    redsubgreen = red.subtract(green)
    redaddgreen = red.add(green)
    return redsubgreen.divide(redaddgreen)

class Air2water_monit:

    def __init__(self, start_date=None, end_date=None, long=None, lat=None, cc=None, satellite=None, variable=None, service_account=None, service_key=None, user_id=0, group_id=0, sim_id=0):
        self.start_date= start_date
        self.end_date= end_date
        self.long= long
        self.lat= lat
        self.cc= cc
        self.satellite=satellite
        self.variable=variable
        self.service_account=service_account
        self.service_key=service_key
        self.user_id=user_id
        self.group_id=group_id
        self.sim_id=sim_id

    def atmosphericcorrection_landsat(self, L8, geometry, start_date, end_date, cc):
        # Filter the image collection
        filter = L8.filterBounds(geometry).filterDate(start_date, end_date).filterMetadata('CLOUD_COVER', 'less_than',
                                                                                           cc)

        def maskclouds(image):
            qa = image.select('QA_PIXEL')

            # Bits 2 and 3 are clouds and cirrus, respectively
            cloudBitMask = 1 << 2
            cirrusBitMask = 1 << 3

            # Both flags should be set to zero, indicating clear conditions
            mask = qa.bitwiseAnd(cloudBitMask).eq(0).And(qa.bitwiseAnd(cirrusBitMask).eq(0))

            return image.updateMask(mask)

        filter = filter.map(maskclouds)
        filter = filter.select(ee.List.sequence(0, 10))
        print('Original Image:', filter)

        count = filter.size()
        # Check if we have images
        errorgen = ee.Number(count)
        print('Number of images to be processed:', errorgen.getInfo())

        if errorgen.getInfo():
            filterlist = filter.toList(count)
            imagearray = ee.List.sequence(0, count.subtract(1))

            # Convert to TOA reflectance
            def TOAReflectanceCalc(i):
                i = ee.Number(i).toInt()
                image = ee.Image(filterlist.get(i))
                return ee.Algorithms.Landsat.TOA(image)

            TOAReflectance = ee.ImageCollection(imagearray.map(TOAReflectanceCalc))
            TOAcount = TOAReflectance.size()
            TOAReflectancelist = ee.List(TOAReflectance.toList(TOAcount))

            print('TOAReflectance:', TOAReflectance)

            # Function to calculate dark objects for DOS correction
            def getHistData(image):
                # Get band names
                band = image.bandNames()
                bandseq = ee.List.sequence(0, band.size().subtract(1))

                def histogramfunction(j):
                    j = ee.Number(j).toInt()
                    j1 = ee.String(band.get(j))

                    # Calculate histogram
                    histogram = image.select(j1).reduceRegion(
                        reducer=ee.Reducer.histogram(maxBuckets=2 ** 8),
                        geometry=image.geometry(),
                        scale=10,
                        maxPixels=1e10
                    )

                    # Get histogram data
                    dnList = ee.Array(ee.Dictionary(histogram.get(j1)).get('bucketMeans'))
                    countsList = ee.Array(ee.Dictionary(histogram.get(j1)).get('histogram'))
                    signum = countsList.signum()
                    countsnonzero = countsList.mask(signum).toList()
                    countsnonzerofirst = ee.Number(countsnonzero.get(0))
                    countsList = countsList.toList()
                    index = countsList.indexOf(countsnonzerofirst)
                    dnList = dnList.toList()
                    darkobject = ee.Number(dnList.get(index))
                    darkobjectnext = ee.Number(dnList.get(index.add(1)))

                    # Apply conditions for dark object selection
                    DOS = ee.Algorithms.If(
                        darkobjectnext.subtract(darkobject).lt(ee.Number(100)),
                        darkobject,
                        ee.Number(0).toDouble()
                    )
                    DOS = ee.Algorithms.If(
                        darkobject.lt(ee.Number(0)),
                        ee.Number(0).toDouble(),
                        darkobject
                    )

                    return ee.Image.constant(DOS)

                return ee.ImageCollection(bandseq.map(histogramfunction)).toBands()

            # Calculate dark objects
            Darkobjects = filter.map(getHistData)
            print('Darkobjects:', Darkobjects)

            # Get red band dark objects for scattering calculations
            RedBandObject = Darkobjects.select(3)

            listredbandobjects = ee.List(RedBandObject.toList(RedBandObject.size()))
            redbandobjectsize = listredbandobjects.size()
            iterator = ee.List.sequence(0, redbandobjectsize.subtract(1))
            filterobjects = ee.List(filter.toList(filter.size()))

            # Calculate red band reflectance values
            def redconstantcalc(i):
                i = ee.Number(i).toInt()
                image = ee.Image(listredbandobjects.get(i))

                # Get reflectance conversion parameters
                reflectancemult = ee.Image(filterobjects.get(i)).get('REFLECTANCE_MULT_BAND_4')
                reflectanceadd = ee.Image(filterobjects.get(i)).get('REFLECTANCE_ADD_BAND_4')
                sunele = ee.Image(filterobjects.get(i)).get('SUN_ELEVATION')
                sinsunele = ee.Number(sunele).sin()

                # Calculate mean DN value
                mean = image.reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=geometry,
                    scale=10,
                    maxPixels=1e10
                )

                redbanddn = ee.Number(mean.get(ee.String(mean.keys().get(0))))
                redref = ((redbanddn.multiply(reflectancemult)).add(reflectanceadd)).divide(sinsunele)

                return redref

            redscatter = iterator.map(redconstantcalc)

            # Calculate scattering for other bands based on red band
            def bluegreenNIRref(j):
                j = ee.Number(j).toInt()
                redref = ee.Number(redscatter.get(j))

                # Model relationships between red and other bands for scattering
                blueref = (((redref.multiply(redref)).multiply(ee.Number(-13.2702248))).add(
                    redref.multiply(ee.Number(1.86614321)))).add(ee.Number(0.03290906))
                greenref = (((redref.multiply(redref)).multiply(ee.Number(-6.61392097))).add(
                    redref.multiply(ee.Number(1.5371034)))).add(ee.Number(0.00805925))
                NIRref = (((redref.multiply(redref)).multiply(ee.Number(6.50869749))).add(
                    redref.multiply(ee.Number(0.2685842)))).subtract(ee.Number(0.00101387))

                return ee.Feature(None, {
                    'bluescatter': blueref,
                    'greenscatter': greenref,
                    'NIRscatter': NIRref
                })

            scatter = ee.FeatureCollection(iterator.map(bluegreenNIRref))

            # Extract scattering values
            bluescatter = scatter.aggregate_array('bluescatter')
            greenscatter = scatter.aggregate_array('greenscatter')
            NIRscatter = scatter.aggregate_array('NIRscatter')

            # Extract TOA reflectance for each band
            bluereflectance = TOAReflectance.select(1).toList(TOAReflectance.size())
            greenreflectance = TOAReflectance.select(2).toList(TOAReflectance.size())
            redreflectance = TOAReflectance.select(3).toList(TOAReflectance.size())
            NIRreflectance = TOAReflectance.select(4).toList(TOAReflectance.size())

            # Calculate surface reflectance for each band
            def bluesurfacereflectancecalculator(l):
                l = ee.Number(l).toInt()
                blueimage = ee.Image(bluereflectance.get(l))
                bluescattervalue = ee.Number(bluescatter.get(l))
                bluescatterimage = ee.Image.constant(ee.List.repeat(bluescattervalue, blueimage.bandNames().length()))
                return blueimage.subtract(bluescatterimage)

            def greensurfacereflectancecalculator(l):
                l = ee.Number(l).toInt()
                greenimage = ee.Image(greenreflectance.get(l))
                greenscattervalue = ee.Number(greenscatter.get(l))
                greenscatterimage = ee.Image.constant(
                    ee.List.repeat(greenscattervalue, greenimage.bandNames().length()))
                return greenimage.subtract(greenscatterimage)

            def redsurfacereflectancecalculator(l):
                l = ee.Number(l).toInt()
                redimage = ee.Image(redreflectance.get(l))
                redscattervalue = ee.Number(redscatter.get(l))
                redscatterimage = ee.Image.constant(ee.List.repeat(redscattervalue, redimage.bandNames().length()))
                return redimage.subtract(redscatterimage)

            def NIRsurfacereflectancecalculator(l):
                l = ee.Number(l).toInt()
                NIRimage = ee.Image(NIRreflectance.get(l))
                NIRscattervalue = ee.Number(NIRscatter.get(l))
                NIRscatterimage = ee.Image.constant(ee.List.repeat(NIRscattervalue, NIRimage.bandNames().length()))
                return NIRimage.subtract(NIRscatterimage)

            # Apply surface reflectance calculators
            blueSR = iterator.map(bluesurfacereflectancecalculator)
            greenSR = iterator.map(greensurfacereflectancecalculator)
            redSR = iterator.map(redsurfacereflectancecalculator)
            NIRSR = iterator.map(NIRsurfacereflectancecalculator)

            # Create composite surface reflectance images
            def compositeSRmaker(i):
                i = ee.Number(i).toInt()
                blueSRi = ee.Image(blueSR.get(i)).rename('B2')
                greenSRi = ee.Image(greenSR.get(i)).rename('B3')
                redSRi = ee.Image(redSR.get(i)).rename('B4')
                NIRSRi = ee.Image(NIRSR.get(i)).rename('B5')
                SWIR1i = ee.Image(TOAReflectancelist.get(i)).select(5).rename('B6')
                SWIR2i = ee.Image(TOAReflectancelist.get(i)).select(6).rename('B7')
                return ee.Image([blueSRi, greenSRi, redSRi, NIRSRi, SWIR1i, SWIR2i])

            compositeSR = ee.ImageCollection(iterator.map(compositeSRmaker))
            print('Surface Reflectance for Blue, Green, Red, NIR, SWIR 1 and SWIR2:', compositeSR)

            return compositeSR

        # Return empty collection if no images found
        return filter

    def atmosphericcorrection_sentinel(self, S2, geometry, startdate, enddate, cc):
        # Filter the image collection
        filter = (S2.filterBounds(geometry)
                  .filterDate(startdate, enddate)
                  .filterMetadata('CLOUDY_PIXEL_PERCENTAGE', 'less_than', cc))

        def maskS2clouds(image):
            qa = image.select('QA60')
            cloudBitMask = 1 << 10
            cirrusBitMask = 1 << 11
            mask = qa.bitwiseAnd(cloudBitMask).eq(0).And(qa.bitwiseAnd(cirrusBitMask).eq(0))
            return image.updateMask(mask)

        filter = filter.map(maskS2clouds)
        filter = filter.select([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11])

        count = filter.size()
        print('Number of images to be processed:', count.getInfo())

        # Check if we have images
        errorgen = count

        if errorgen.getInfo():
            filterlist = filter.toList(count)
            imagearray = ee.List.sequence(0, count.subtract(1))

            # Convert to TOA reflectance
            def divide10000(image):
                image = image.toFloat()
                return image.divide(10000)

            TOAReflectance = filter.map(divide10000)
            print('TOA Reflectance:', TOAReflectance)

            # Calculate dark objects for DOS correction
            def get_hist_data(image):
                # Get band names
                band = image.bandNames()
                bandseq = ee.List.sequence(0, band.size().subtract(1))

                def histogram_function(j):
                    j = ee.Number(j).toInt()
                    j1 = ee.String(band.get(j))

                    # Generate histogram
                    histogram = image.select(j1).reduceRegion(
                        reducer=ee.Reducer.histogram(maxBuckets=2 ** 8),
                        geometry=image.geometry(),
                        scale=10,
                        maxPixels=1e10
                    )

                    # Get histogram values
                    dnList = ee.Array(ee.Dictionary(histogram.get(j1)).get('bucketMeans'))
                    countsList = ee.Array(ee.Dictionary(histogram.get(j1)).get('histogram'))

                    # Find first non-zero count
                    signum = countsList.signum()
                    countsnonzero = countsList.mask(signum).toList()
                    countsnonzerofirst = ee.Number(countsnonzero.get(0))
                    countsList = countsList.toList()
                    index = countsList.indexOf(countsnonzerofirst)

                    # Get corresponding DN value
                    dnList = dnList.toList()
                    darkobject = ee.Number(dnList.get(index))
                    darkobjectnext = ee.Number(dnList.get(index.add(1)))

                    # Apply conditions for dark object selection
                    DOS = ee.Algorithms.If(
                        darkobjectnext.subtract(darkobject).lt(ee.Number(100)),
                        darkobject,
                        ee.Number(0).toDouble()
                    )
                    DOS = ee.Algorithms.If(
                        darkobject.lt(ee.Number(0)),
                        ee.Number(0).toDouble(),
                        darkobject
                    )

                    return ee.Image.constant(DOS)

                return ee.ImageCollection(bandseq.map(histogram_function)).toBands()

            # Apply DOS to all images
            Darkobjects = TOAReflectance.map(get_hist_data)

            # Subtract minimum radiance (0.01)
            def minradsubtract(image):
                return image.subtract(ee.Number(0.01))

            Darkobjectminrad = Darkobjects.map(minradsubtract)
            print('Dark objects with 0.01 reflectance subtracted:', Darkobjectminrad)

            # Extract red band objects for scattering calculations
            RedBandObject = Darkobjectminrad.select(3)  # Red band index

            listredbandobjects = ee.List(RedBandObject.toList(RedBandObject.size()))
            redbandobjectsize = listredbandobjects.size()
            iterator = ee.List.sequence(0, redbandobjectsize.subtract(1))

            # Calculate red band mean values
            def redconstantcalc(i):
                i = ee.Number(i).toInt()
                image = ee.Image(listredbandobjects.get(i))
                mean = image.reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=geometry,
                    scale=10,
                    maxPixels=1e10
                )
                redbanddn = ee.Number(mean.get(ee.String(mean.keys().get(0))))
                return redbanddn

            redscatter = iterator.map(redconstantcalc)

            # Calculate scattering for other bands based on red band
            def bluegreenrededgesNIRref(j):
                j = ee.Number(j).toInt()
                redref = ee.Number(redscatter.get(j))

                # These equations model the relationship between red band and other bands for scattering
                blueref = (((redref.multiply(redref)).multiply(ee.Number(-13.04998369))).add(
                    redref.multiply(ee.Number(1.87108273)))).add(ee.Number(0.02922965))
                greenref = (((redref.multiply(redref)).multiply(ee.Number(-6.94415673))).add(
                    redref.multiply(ee.Number(1.55908871)))).add(ee.Number(0.00909009))
                rededge1ref = (((redref.multiply(redref)).multiply(ee.Number(2.37917491))).add(
                    redref.multiply(ee.Number(0.78762518)))).subtract(ee.Number(0.00063928))
                rededge2ref = (((redref.multiply(redref)).multiply(ee.Number(3.72973644))).add(
                    redref.multiply(ee.Number(0.64757496)))).subtract(ee.Number(0.00100617))
                rededge3ref = (((redref.multiply(redref)).multiply(ee.Number(5.02460471))).add(
                    redref.multiply(ee.Number(0.50098859)))).subtract(ee.Number(0.00112357))
                NIRref = (((redref.multiply(redref)).multiply(ee.Number(6.2809185))).add(
                    redref.multiply(ee.Number(0.33946616)))).subtract(ee.Number(0.00097318))
                rededge4ref = (((redref.multiply(redref)).multiply(ee.Number(6.64042269))).add(
                    redref.multiply(ee.Number(0.28710159)))).subtract(ee.Number(0.00086581))

                return ee.Feature(None, {
                    'bluescatter': blueref,
                    'greenscatter': greenref,
                    'rededge1': rededge1ref,
                    'rededge2': rededge2ref,
                    'rededge3': rededge3ref,
                    'NIRscatter': NIRref,
                    'rededge4': rededge4ref
                })

            scatter = ee.FeatureCollection(iterator.map(bluegreenrededgesNIRref))

            # Extract scattering values for each band
            bluescatter = scatter.aggregate_array('bluescatter')
            greenscatter = scatter.aggregate_array('greenscatter')
            rededge1scatter = scatter.aggregate_array('rededge1')
            rededge2scatter = scatter.aggregate_array('rededge2')
            rededge3scatter = scatter.aggregate_array('rededge3')
            NIRscatter = scatter.aggregate_array('NIRscatter')
            rededge4scatter = scatter.aggregate_array('rededge4')

            # Extract TOA reflectance for each band
            bluereflectance = TOAReflectance.select(1).toList(TOAReflectance.size())
            greenreflectance = TOAReflectance.select(2).toList(TOAReflectance.size())
            redreflectance = TOAReflectance.select(3).toList(TOAReflectance.size())
            rededge1reflectance = TOAReflectance.select(4).toList(TOAReflectance.size())
            rededge2reflectance = TOAReflectance.select(5).toList(TOAReflectance.size())
            rededge3reflectance = TOAReflectance.select(6).toList(TOAReflectance.size())
            NIRreflectance = TOAReflectance.select(7).toList(TOAReflectance.size())
            rededge4reflectance = TOAReflectance.select(8).toList(TOAReflectance.size())
            SWIR1reflectance = TOAReflectance.select(11).toList(TOAReflectance.size())
            SWIR2reflectance = TOAReflectance.select(12).toList(TOAReflectance.size())

            # Calculate surface reflectance for each band
            def bluesurfacereflectancecalculator(l):
                l = ee.Number(l).toInt()
                blueimage = ee.Image(bluereflectance.get(l))
                bluescattervalue = ee.Number(bluescatter.get(l))
                bluescatterimage = ee.Image.constant(ee.List.repeat(bluescattervalue, blueimage.bandNames().length()))
                return blueimage.subtract(bluescatterimage)

            def greensurfacereflectancecalculator(l):
                l = ee.Number(l).toInt()
                greenimage = ee.Image(greenreflectance.get(l))
                greenscattervalue = ee.Number(greenscatter.get(l))
                greenscatterimage = ee.Image.constant(
                    ee.List.repeat(greenscattervalue, greenimage.bandNames().length()))
                return greenimage.subtract(greenscatterimage)

            def redsurfacereflectancecalculator(l):
                l = ee.Number(l).toInt()
                redimage = ee.Image(redreflectance.get(l))
                redscattervalue = ee.Number(redscatter.get(l))
                redscatterimage = ee.Image.constant(ee.List.repeat(redscattervalue, redimage.bandNames().length()))
                return redimage.subtract(redscatterimage)

            def rededge1surfacereflectancecalculator(l):
                l = ee.Number(l).toInt()
                rededge1image = ee.Image(rededge1reflectance.get(l))
                rededge1scattervalue = ee.Number(rededge1scatter.get(l))
                rededge1scatterimage = ee.Image.constant(
                    ee.List.repeat(rededge1scattervalue, rededge1image.bandNames().length()))
                return rededge1image.subtract(rededge1scatterimage)

            def rededge2surfacereflectancecalculator(l):
                l = ee.Number(l).toInt()
                rededge2image = ee.Image(rededge2reflectance.get(l))
                rededge2scattervalue = ee.Number(rededge2scatter.get(l))
                rededge2scatterimage = ee.Image.constant(
                    ee.List.repeat(rededge2scattervalue, rededge2image.bandNames().length()))
                return rededge2image.subtract(rededge2scatterimage)

            def rededge3surfacereflectancecalculator(l):
                l = ee.Number(l).toInt()
                rededge3image = ee.Image(rededge3reflectance.get(l))
                rededge3scattervalue = ee.Number(rededge3scatter.get(l))
                rededge3scatterimage = ee.Image.constant(
                    ee.List.repeat(rededge3scattervalue, rededge3image.bandNames().length()))
                return rededge3image.subtract(rededge3scatterimage)

            def NIRsurfacereflectancecalculator(l):
                l = ee.Number(l).toInt()
                NIRimage = ee.Image(NIRreflectance.get(l))
                NIRscattervalue = ee.Number(NIRscatter.get(l))
                NIRscatterimage = ee.Image.constant(ee.List.repeat(NIRscattervalue, NIRimage.bandNames().length()))
                return NIRimage.subtract(NIRscatterimage)

            def rededge4surfacereflectancecalculator(l):
                l = ee.Number(l).toInt()
                rededge4image = ee.Image(rededge4reflectance.get(l))
                rededge4scattervalue = ee.Number(rededge4scatter.get(l))
                rededge4scatterimage = ee.Image.constant(
                    ee.List.repeat(rededge4scattervalue, rededge4image.bandNames().length()))
                return rededge4image.subtract(rededge4scatterimage)

            # Map surface reflectance calculators to all images
            blueSR = iterator.map(bluesurfacereflectancecalculator)
            greenSR = iterator.map(greensurfacereflectancecalculator)
            redSR = iterator.map(redsurfacereflectancecalculator)
            rededge1SR = iterator.map(rededge1surfacereflectancecalculator)
            rededge2SR = iterator.map(rededge2surfacereflectancecalculator)
            rededge3SR = iterator.map(rededge3surfacereflectancecalculator)
            NIRSR = iterator.map(NIRsurfacereflectancecalculator)
            rededge4SR = iterator.map(rededge4surfacereflectancecalculator)

            # Create composite surface reflectance images
            def compositeSRmaker(i):
                i = ee.Number(i).toInt()
                blueSRi = ee.Image(blueSR.get(i)).rename('B2')
                greenSRi = ee.Image(greenSR.get(i)).rename('B3')
                redSRi = ee.Image(redSR.get(i)).rename('B4')
                rededge1SRi = ee.Image(rededge1SR.get(i)).rename('B5')
                rededge2SRi = ee.Image(rededge2SR.get(i)).rename('B6')
                rededge3SRi = ee.Image(rededge3SR.get(i)).rename('B7')
                NIRSRi = ee.Image(NIRSR.get(i)).rename('B8')
                rededge4SRi = ee.Image(rededge4SR.get(i)).rename('B8A')
                SWIR1SRi = ee.Image(SWIR1reflectance.get(i)).rename('B11')
                return ee.Image(
                    [blueSRi, greenSRi, redSRi, rededge1SRi, rededge2SRi, rededge3SRi, NIRSRi, rededge4SRi, SWIR1SRi])

            compositeSR = ee.ImageCollection(iterator.map(compositeSRmaker))

            print(
                'Surface Reflectance for Blue, Green, Red, Red Edge (Band 5), Red Edge (Band 6), Red Edge (Band 7), NIR, Red Edge (Band 8a), and SWIR (Band 11):',
                compositeSR)
            return compositeSR

        return filter  # Return filtered images if no images found

    def CI_Landsat(self, imageCollection):

        def mapCIlandsat(image):
            red = image.select(2)
            green = image.select(1)
            return CIcalc(red,green)


        MNDWI = imageCollection.map(mapMNDWIlandsat)
        MNDWIextract = MNDWI.select('B[2-8]')
        print('MNDWI Images', MNDWIextract)

        NDCI = MNDWI.map(mapCIlandsat).select(['B4'], ['Chlorophyllindex'])

        return ee.Feature(None, {
            'MNDWIimage': MNDWIextract,
            'Chlorophyllindex': NDCI
        })

    def CI_Sentinel(self, imageCollection):
        def mapCIsentinel(image):
            rededge = image.select(3)
            red = image.select(2)
            return CIcalc(rededge,red)


        MNDWI = imageCollection.map(mapMNDWIsentinel)
        MNDWIextract = MNDWI.select('B[1-9]')
        print('MNDWI Images', MNDWIextract)

        NDCI = MNDWI.map(mapCIsentinel).select(['B5'], ['Chlorophyllindex'])

        return ee.Feature(None, {
            'MNDWIimage': MNDWIextract,
            'Chlorophyllindex': NDCI
        })

    def TI_Sentinel(self, imageCollection):
        def mapCIsentinel(image):
            green = image.select(1)
            red = image.select(2)
            return CIcalc(red,green)


        MNDWI = imageCollection.map(mapMNDWIsentinel)
        MNDWIextract = MNDWI.select('B[1-9]')
        print('MNDWI Images', MNDWIextract)

        NDTI = MNDWI.map(mapCIsentinel).select(['B4'], ['Turbidityindex'])

        return ee.Feature(None, {
            'MNDWIimage': MNDWIextract,
            'Turbidityindex': NDTI
        })

    def DO_Landsat(self,imageCollection):
        def DOcalc(image):
            blue = image.select(0)
            green = image.select(1)
            NIR = image.select(3)

            bluebyNIR = blue.divide(NIR)
            greenbyNIR = green.divide(NIR)

            constant = ee.Image.constant(8.2)
            DO = (constant.subtract(bluebyNIR.multiply(ee.Number(0.15)))
                  .add(greenbyNIR.multiply(ee.Number(0.32))))

            return DO.rename('Dissolvedoxygen')

        MNDWI = imageCollection.map(mapMNDWIlandsat)
        MNDWIextract = MNDWI.select('B[2-8]')
        print('MNDWI Images', MNDWIextract)

        DO = MNDWI.map(DOcalc).select(['Dissolvedoxygen'])

        return ee.Feature(None, {'Dissolvedoxygen': DO})

    def DO_Sentinel(self,imageCollection):
        def DOcalc(image):
            rededge1 = image.select(3)
            narrowNIR = image.select(7)
            red = image.select(2)
            rededge3 = image.select(5)
            NIR = image.select(6)

            NIRsubred = NIR.subtract(red)
            NIRaddred = NIR.add(red)

            fraction1 = rededge1.divide(red.add(narrowNIR))
            fraction2 = red.divide(rededge3.subtract(NIR))

            constant = ee.Image.constant(1.687)
            DO = (constant.add(fraction1.multiply(ee.Number(13.65)))
                  .subtract(fraction2.multiply(ee.Number(0.3714))))

            return DO.rename('Dissolvedoxygen')

        MNDWI = imageCollection.map(mapMNDWIsentinel)
        MNDWIextract = MNDWI.select('B[1-9]')
        print('MNDWI Images', MNDWIextract)

        DO = MNDWI.map(DOcalc).select(['Dissolvedoxygen'])

        return ee.Feature(None, {'Dissolvedoxygen': DO})

    def find_nearest_feature(self, fc, point):
        # Compute distances from the point to each feature in the collection
        distances = fc.map(lambda feature: feature.set('distance', feature.geometry().distance(point)))

        # Sort by distance and get the nearest feature
        nearest_feature = distances.sort('distance').first()
        return nearest_feature

    def map_clip_function(self,image_collection, buffered_shapefile):
        return image_collection.map(lambda image: image.clip(buffered_shapefile))

    def run(self):
        owd = settings.MEDIA_ROOT
        # Initialize Google Earth Engine
        try:
            service_account = self.service_account
            credentials = ee.ServiceAccountCredentials(service_account, self.service_key)
            ee.Initialize(credentials)
        except ee.EEException as e:
            print(str(e))

        self.cc = ee.Number(self.cc)
        self.geometry = ee.Geometry.Point([self.lat, self.long], 'EPSG:4326')
        self.start_date = ee.Date(str(self.start_date))
        self.end_date = ee.Date(str(self.end_date))

        # Get parameter name for title
        parameter_names = {
            1: 'Chlorophyll-a',
            2: 'Turbidity',
            3: 'Dissolved Oxygen'
        }
        satellite_names = {
            1: 'Landsat',
            2: 'Sentinel'
        }

        parameter_name = parameter_names.get(self.variable, 'Unknown Parameter')
        satellite_name = satellite_names.get(self.satellite, 'Unknown Satellite')

        # Create base folium map centered on the point of interest
        m = folium.Map(
            location=[self.long, self.lat],
            zoom_start=10
        )

        # Add title to map
        title_html = '''
            <div style="position: fixed; 
                        top: 10px; 
                        left: 50px; 
                        width: 500px; 
                        height: 90px; 
                        z-index:9999; 
                        background-color: rgba(255, 255, 255, 0.8);
                        border-radius: 10px;
                        padding: 10px;
                        font-size: 16px;
                        font-weight: bold;">
                <p>{} Monitoring Results<br>
                {} Data from {} to {}<br>
                Location: {:.3f}°N, {:.3f}°E</p>
            </div>
            '''.format(
            parameter_name,
            satellite_name,
            self.start_date.format('YYYY-MM-dd').getInfo(),
            self.end_date.format('YYYY-MM-dd').getInfo(),
            self.long,
            self.lat
        )
        m.get_root().html.add_child(folium.Element(title_html))

        # Get and process lake data
        self.table = ee.FeatureCollection("projects/sat-io/open-datasets/HydroLakes/lake_poly_v10")
        filtered_table = self.table.filterBounds(self.geometry.buffer(300000))
        nearest_feature = self.find_nearest_feature(filtered_table, self.geometry)
        shapefile = ee.Feature(nearest_feature)
        buffered_shapefile = shapefile.buffer(1000)

        # Add lake boundary to map
        lake_coords = ee.Feature(nearest_feature).geometry().coordinates().getInfo()
        folium.GeoJson(
            data={
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": lake_coords
                }
            },
            style_function=lambda x: {"fillColor": "blue", "color": "blue", "weight": 2, "fillOpacity": 0.1}
        ).add_to(m)

        # Define color palettes based on parameter
        if self.variable == 1:  # Chlorophyll-a
            color_palette = ['#313695', '#4575B4', '#74ADD1', '#ABD9E9', '#E0F3F8',
                             '#FFFFBF', '#FEE090', '#FDAE61', '#F46D43', '#D73027', '#A50026']
            legend_title = 'Chlorophyll-a (NDCI)'
            value_range = [-1, 1]  # Fallback range if statistics fail
        elif self.variable == 2:  # Turbidity
            color_palette = ['#313695', '#4575B4', '#74ADD1', '#ABD9E9', '#E0F3F8',
                             '#FFFFBF', '#FEE090', '#FDAE61', '#F46D43', '#D73027', '#A50026']
            legend_title = 'Turbidity (NDTI)'
            value_range = [-1, 1]  # Fallback range if statistics fail
        else:  # Dissolved Oxygen
            color_palette = ['#A50026', '#D73027', '#F46D43', '#FDAE61', '#FEE090',
                             '#FFFFBF', '#E0F3F8', '#ABD9E9', '#74ADD1', '#4575B4', '#313695']
            legend_title = 'Dissolved Oxygen (mg/L)'
            value_range = [0, 20]  # Fallback range if statistics fail

        # Get and process satellite data
        if self.satellite == 1:
            tile = ee.ImageCollection("LANDSAT/LC08/C02/T1")
            tile = self.map_clip_function(tile, buffered_shapefile)
            Reflectance = self.atmosphericcorrection_landsat(tile, self.geometry, self.start_date, self.end_date,
                                                             self.cc)

            if self.variable == 1:
                result = ee.ImageCollection(self.CI_Landsat(Reflectance).get('Chlorophyllindex'))
                layer_name = 'Chlorophyll Index'
            elif self.variable == 2:
                result = ee.ImageCollection(self.CI_Landsat(Reflectance).get('Chlorophyllindex'))
                layer_name = 'Turbidity Index'
            elif self.variable == 3:
                result = ee.ImageCollection(self.DO_Landsat(Reflectance).get('Dissolvedoxygen'))
                layer_name = 'Dissolved Oxygen'

        elif self.satellite == 2:
            tile = ee.ImageCollection("COPERNICUS/S2")
            tile = self.map_clip_function(tile, buffered_shapefile)
            Reflectance = self.atmosphericcorrection_sentinel(tile, self.geometry, self.start_date, self.end_date,
                                                              self.cc)

            if self.variable == 1:
                result = ee.ImageCollection(self.CI_Sentinel(Reflectance).get('Chlorophyllindex'))
                layer_name = 'Chlorophyll Index'
            elif self.variable == 2:
                result = ee.ImageCollection(self.TI_Sentinel(Reflectance).get('Turbidityindex'))
                layer_name = 'Turbidity Index'
            elif self.variable == 3:
                result = ee.ImageCollection(self.DO_Sentinel(Reflectance).get('Dissolvedoxygen'))
                layer_name = 'Dissolved Oxygen'

            # Get statistics from the image for dynamic visualization range
            try:
                # First, debug what band names are actually present
                first_image = result.first()
                print("Available bands:", first_image.bandNames().getInfo())

                # Select the first band and rename it to 'value' for consistent analytics
                # This is important because we don't know exactly what the band is named in the result
                first_band = first_image.bandNames().get(0)
                image_with_renamed_band = first_image.select([first_band], ['value'])

                # Create combined reducer for mean and standard deviation
                meanStdDev = ee.Reducer.mean().combine(
                    reducer2=ee.Reducer.stdDev(),
                    sharedInputs=True
                ).setOutputs(['mean', 'stddev'])

                # Calculate mean and standard deviation of the image values
                stats = image_with_renamed_band.reduceRegion(
                    reducer=meanStdDev,
                    geometry=shapefile.geometry(),
                    scale=30,
                    bestEffort=True,
                    maxPixels=1e10
                )

                print("Stats:", stats.getInfo())  # Debug the stats dictionary

                # Number of standard deviations to use for visualization range
                num_stddev = 2.5

                # Calculate min and max values for visualization based on mean and stddev
                vis_min = ee.Number(stats.get('value_mean')).subtract(
                    ee.Number(num_stddev).multiply(ee.Number(stats.get('value_stddev'))))
                vis_max = ee.Number(stats.get('value_mean')).add(
                    ee.Number(num_stddev).multiply(ee.Number(stats.get('value_stddev'))))

                # Ensure we have real values for vis_min and vis_max
                vis_min_value = vis_min.getInfo()
                vis_max_value = vis_max.getInfo()

                print(f"Dynamic range: min={vis_min_value}, max={vis_max_value}")

                # Check if the values are valid
                if (vis_min_value is None or vis_max_value is None or
                        not np.isfinite(vis_min_value) or not np.isfinite(vis_max_value) or
                        vis_min_value >= vis_max_value):
                    raise ValueError("Invalid statistics values")

            except Exception as e:
                print(f"Error calculating dynamic range: {str(e)}")
                # Fallback to predefined range if any error occurs
                vis_min_value = value_range[0]
                vis_max_value = value_range[1]

            print(f"Final visualization range: min={vis_min_value}, max={vis_max_value}")

            # Generate thumbnail with the calculated value range
            thumb_url = result.first().getThumbUrl({
                'min': vis_min_value,
                'max': vis_max_value,
                'dimensions': 1024,
                'format': 'png',
                'palette': color_palette
            })
            response = requests.get(thumb_url)
            img = Image.open(BytesIO(response.content)).convert("RGBA")

            # Convert the image to a numpy array
            array = np.array(img)

            # Extract the red channel and the alpha channel
            red_channel = array[:, :, 0]
            alpha_channel = array[:, :, 3]

            # Mask out the transparent pixels
            masked_red_channel = np.ma.masked_where(alpha_channel == 0, red_channel)

            # Plot the masked array with the SAME value range as the map
            plt.figure(figsize=[8, 8])
            plt.imshow(masked_red_channel, cmap="jet", origin="upper", vmin=0, vmax=255)

            # Create a custom colorbar with the actual value range
            cbar = plt.colorbar(shrink=0.8, label=legend_title)

            # Set the colorbar ticks to match the calculated value range
            old_ticks = np.linspace(0, 255, 6)
            new_tick_values = np.linspace(vis_min_value, vis_max_value, 6)
            cbar.set_ticks(old_ticks)
            cbar.set_ticklabels([f"{v:.2f}" for v in new_tick_values])

            plt.axis('off')
            plt.tight_layout()
            plt.savefig(
                f"{owd}/monitoring_results/{self.user_id}_{self.group_id}/{self.satellite}_{self.variable}_{self.sim_id}.png",
                dpi=100)

            # Add result as a tile layer - using the same dynamic value range
            map_id_dict = result.first().getMapId({
                'min': vis_min_value,
                'max': vis_max_value,
                'palette': color_palette
            })

            folium.TileLayer(
                tiles=map_id_dict['tile_fetcher'].url_format,
                attr='Google Earth Engine',
                name=layer_name,
                overlay=True,
                control=True
            ).add_to(m)

            # Add colormap legend with the dynamically calculated values
            legend_vals = np.linspace(vis_max_value, vis_min_value, len(color_palette))
            legend_vals = ['{:.2f}'.format(v) for v in legend_vals]

            legend_html = '''
                       <div style="position: fixed; 
                                   bottom: 50px; 
                                   right: 50px; 
                                   width: 180px;
                                   z-index:9999; 
                                   background-color: rgba(255, 255, 255, 0.8);
                                   border-radius: 10px;
                                   padding: 10px;
                                   font-family: sans-serif;
                                   font-size: 12px;">
                           <p style="margin: 0 0 10px 0; font-size: 13px; font-weight: bold;">{}</p>
                           <div style="display: flex; flex-direction: column; gap: 3px;">
                   '''.format(legend_title)

            for value, color in zip(legend_vals, color_palette):
                legend_html += '''
                           <div style="display: flex; align-items: center; height: 15px;">
                               <div style="min-width: 20px; height: 15px; background-color: {}; margin-right: 8px;"></div>
                               <span style="white-space: nowrap;">{}</span>
                           </div>
                       '''.format(color, value)

            legend_html += '''
                           </div>
                       </div>
                   '''

            m.get_root().html.add_child(folium.Element(legend_html))

            # Add layer control
            folium.LayerControl().add_to(m)

            # Return the HTML representation of the map
            return m._repr_html_()

if __name__ == "__main__":
    Run = Air2water_monit(start_date='2022-03-01',end_date='2022-12-15',lat=10.683,long=45.667, cc=7, satellite=2, variable=2, service_account='hydrosquas-monitoring@ee-hydrosquas-riddick.iam.gserviceaccount.com' , service_key='/home/riddick/Downloads/ee-hydrosquas-riddick-a7cc9060a474.json')
    folium=Run.run()
    print(thumb)