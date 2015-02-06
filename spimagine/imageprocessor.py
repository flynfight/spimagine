"""
Implements generic classes for processing of volumetric data
"""

import numpy as np
import imgtools
import lucy_richardson_gpu


class ImageProcessor(object):
    def __init__(self,name = "",**kwargs):
        self.name = name
        self.set_params(**kwargs)

    def set_params(self,**kwargs):
        self.kwargs = kwargs

    def apply(self, data):
        raise NotImplementedError()

    def __getattr__(self,attr):
        if self.kwargs.has_key(attr):
            return self.kwargs[attr]
        else:
            return super(ImageProcessor,self).__getattr__(attr)



class CopyProcessor(ImageProcessor):

    def __init__(self):
        super(CopyProcessor,self).__init__("copy")

    def apply(self,data):
        return data

import PyOCL

class BlurProcessor(ImageProcessor):

    def __init__(self,size = 7):
        super(BlurProcessor,self).__init__("blur",size = size)

    def apply(self,data):
        x = np.linspace(-1.,1.,self.size)
        h = np.exp(-4.*x**2)
        h *= 1./sum(h)
        return imgtools.convolve_sep3(data, h, h, h)

class NoiseProcessor(ImageProcessor):

    def __init__(self,sigma = 10):
        super(NoiseProcessor,self).__init__("noise",sigma = sigma)

    def apply(self,data):
        return np.maximum(0,data+self.sigma*np.random.normal(0,1,data.shape))


class FFTProcessor(ImageProcessor):
    def __init__(self, isLog = False):
        super(FFTProcessor,self).__init__("fft")
        self.isLog = isLog

    def apply(self,data):
        res = np.fft.fftshift(abs(imgtools.ocl_fft(data)))
        if self.isLog:
            return np.log(res)
        else:
            return res


class LucyRichProcessor(ImageProcessor):

    def __init__(self,rad = 4., niter = 10):
        super(LucyRichProcessor,self).__init__("RL-Deconv",rad = rad, niter = niter)
        self.rad0 = rad
        self.niter0 = niter
        self.hshape = (1,)*3

    def reset_psf(self,dshape):
        self.h = imgtools.blur_psf(dshape,self.rad)


    def apply(self,data):
        if self.hshape != data.shape or self.rad != self.rad0:
            self.reset_psf(data.shape)
            self.rad0 = self.rad


        return lucy_richardson_gpu.lucy_richardson(data, self.h,self.niter)




if __name__ == '__main__':
    from numpy import *


    p = LucyRichProcessor()


    Z,Y,X = imgtools.ZYX(128)

    u = 100*exp(-100*(X**2+Y**2+Z**2))

    # u += 10.*np.random.normal(0,1.,u.shape)


    y = p.apply(u)