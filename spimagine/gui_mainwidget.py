#!/usr/bin/env python

"""
the main frame used for in spimagine_gui

the data model is member of the frame

author: Martin Weigert
email: mweigert@mpi-cbg.de
"""



import os
import numpy as np
import sys

from PyQt4 import QtCore
from PyQt4 import QtGui

from spimagine.quaternion import Quaternion
from spimagine.gui_glwidget import GLWidget

from spimagine.keyframe_model import KeyFrameList

from spimagine.keyframe_view import KeyFramePanel
from spimagine.gui_settings import SettingsPanel
from spimagine.data_model import DataModel, DemoData, SpimData, TiffData
from spimagine import egg3d

from spimagine.gui_slice_view import SliceWidget

from spimagine.transform_model import TransformModel

from spimagine.gui_utils import *


import logging
logger = logging.getLogger(__name__)

# logger.setLevel(logging.DEBUG)



# the default number of data timeslices to prefetch
N_PREFETCH = 10


def absPath(myPath):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    import sys

    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
        logger.debug("found MEIPASS: %s "%os.path.join(base_path, os.path.basename(myPath)))

        return os.path.join(base_path, os.path.basename(myPath))
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
        return os.path.join(base_path, myPath)



class MainWidget(QtGui.QWidget):
    N_SCALE_MIN_EXP = -16
    N_SCALE_MAX_EXP = 16
    N_SCALE_SLIDER = 500
    N_GAMMA_SLIDER = 200

    def __init__(self, parent = None):
        super(QtGui.QWidget,self).__init__(parent)

        self.myparent = parent

        self.isCloseFlag = False


        self.isFullScreen = False
        self.setWindowTitle('SpImagine')

        self.resize(900, 700)


        self.transform = TransformModel()

        self.initActions()
        # self.initMenus()

        self.glWidget = GLWidget(self)
        self.glWidget.setTransform(self.transform)

        self.sliceWidget = SliceWidget(self)
        self.sliceWidget.hide()


        self.sliceWidget.setTransform(self.transform)

        self.fwdButton = createStandardButton(self,
                fName = absPath("images/icon_forward.png"),
                method = self.forward, width = 18, tooltip="forward")
        self.bwdButton = createStandardButton(self,
                fName = absPath("images/icon_backward.png"),
                method = self.backward, width = 18, tooltip="backward")

        self.startButton = createStandardButton(self, fName = absPath("images/icon_start.png"),
                                                method = self.startPlay, tooltip="play")



        self.centerButton = createStandardButton(self, fName = absPath("images/icon_center.png"),
                                                 method = self.center, tooltip = "center view")

        self.rotateButton = createStandardButton(self, fName = absPath("images/icon_rotate.png"),
                                                 method = self.rotate, tooltip = "spin current view")

        self.screenshotButton = createStandardButton(self, fName = absPath("images/icon_camera.png"),
                                                method = self.screenShot, tooltip = "save as png")


        self.checkSettings = createStandardCheckbox(self,absPath("images/settings.png"),
                                                    absPath("images/settings_inactive.png"), tooltip="settings")
        self.checkKey = createStandardCheckbox(self,absPath("images/video.png"),absPath("images/video_inactive.png"), tooltip="keyframe editor")

        self.checkSliceView = createStandardCheckbox(self,absPath("images/icon_slice.png"),
                                                     absPath("images/icon_slice_inactive.png"), tooltip="slice view")


        self.sliderTime = QtGui.QSlider(QtCore.Qt.Horizontal)
        self.sliderTime.setTickPosition(QtGui.QSlider.TicksBothSides)
        self.sliderTime.setTickInterval(1)
        self.sliderTime.setFocusPolicy(QtCore.Qt.ClickFocus)

        self.sliderTime.setTracking(False)


        self.spinTime = QtGui.QSpinBox()
        self.spinTime.setStyleSheet("color:white;")
        self.spinTime.setButtonSymbols(QtGui.QAbstractSpinBox.NoButtons)
        self.spinTime.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.spinTime.setAttribute(QtCore.Qt.WA_MacShowFocusRect, 0)


        self.sliderTime.valueChanged.connect(self.spinTime.setValue)
        self.spinTime.valueChanged.connect(self.sliderTime.setValue)


        self.scaleSlider = QtGui.QSlider(QtCore.Qt.Vertical)

        self.scaleSlider.setRange(1, self.N_SCALE_SLIDER)
        self.scaleSlider.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.scaleSlider.setToolTip("value scale")

        self.gammaSlider = QtGui.QSlider(QtCore.Qt.Vertical)
        self.gammaSlider.setRange(0, self.N_GAMMA_SLIDER)
        self.gammaSlider.setToolTip("value gamma")

        self.gammaSlider.setFocusPolicy(QtCore.Qt.ClickFocus)

        self.gammaSlider.setValue(50)

        # self.scaleSlider.valueChanged.connect(
        #     lambda x: self.transform.setValueScale(0,x**2))
        # self.transform._maxChanged.connect(
        #     lambda x: self.scaleSlider.setValue(int(np.sqrt(x))))

        def func_from_n(n):
            return 2**(self.N_SCALE_MIN_EXP+(self.N_SCALE_MAX_EXP-self.N_SCALE_MIN_EXP)*(n-1.)/(self.N_SCALE_SLIDER-1))


        def func_to_n(x):
            if x<2**self.N_SCALE_MIN_EXP:
                print "gg", x
                return 1
            elif x>2**self.N_SCALE_MAX_EXP:
                return self.N_SCALE_SLIDER

            return int(round(1.+(self.N_SCALE_SLIDER-1.)*(np.log2(x)-self.N_SCALE_MIN_EXP)/(self.N_SCALE_MAX_EXP-1.*self.N_SCALE_MIN_EXP)))


        self.scaleSlider.valueChanged.connect(lambda x: self.transform.setValueScale(0,func_from_n(x)))
        self.transform._maxChanged.connect(lambda x: self.scaleSlider.setValue(func_to_n(x)))


        gammaMin, gammaMax = .25, 2.
        self.gammaSlider.valueChanged.connect(
            lambda x: self.transform.setGamma(gammaMin+x/200.*(gammaMax-gammaMin)))
        self.transform._gammaChanged.connect(
            lambda gam: self.gammaSlider.setValue(200*(gam-gammaMin)/(gammaMax-gammaMin)))


        # self.keyframes = KeyFrameList()
        self.keyPanel = KeyFramePanel(self.glWidget)
        self.keyPanel.hide()

        self.settingsView = SettingsPanel()
        self.settingsView.hide()

        self.setStyleSheet("""
        background-color:black;
        color:white;
        """)

        hbox0 = QtGui.QHBoxLayout()
        hbox0.addWidget(self.scaleSlider)
        hbox0.addWidget(self.gammaSlider)

        hbox0.addWidget(self.glWidget,stretch =1)

        hbox0.addWidget(self.sliceWidget,stretch =1)

        hbox0.addWidget(self.settingsView)

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.bwdButton)
        hbox.addWidget(self.startButton)
        hbox.addWidget(self.fwdButton)
        hbox.addWidget(self.sliderTime)
        hbox.addWidget(self.spinTime)
        # hbox.addWidget(self.checkProj)
        # hbox.addWidget(self.checkBox)

        hbox.addWidget(self.centerButton)

        hbox.addWidget(self.rotateButton)

        hbox.addWidget(self.checkKey)
        hbox.addWidget(self.screenshotButton)

        hbox.addSpacing(50)
        hbox.addWidget(self.checkSliceView)

        hbox.addWidget(self.checkSettings)

        vbox = QtGui.QVBoxLayout()
        vbox.addLayout(hbox0)

        vbox.addLayout(hbox)
        vbox.addWidget(self.keyPanel)


        for box in [hbox,vbox,hbox0]:
            box.setContentsMargins(0,0,0,0)

        vbox.setSpacing(1)
        hbox.setSpacing(11)
        hbox0.setSpacing(5)


        self.egg3d = egg3d.Egg3dController()

        # widget = QtGui.QWidget()
        self.setLayout(vbox)



        self.rotateTimer = QtCore.QTimer(self)
        self.rotateTimer.setInterval(70)
        self.rotateTimer.timeout.connect(self.onRotateTimer)

        self.playTimer = QtCore.QTimer(self)
        self.playTimer.setInterval(100)
        self.playTimer.timeout.connect(self.onPlayTimer)
        self.settingsView._playIntervalChanged.connect(self.playIntervalChanged)
        self.setLoopBounce(True)

        self.playDir = 1

        self.settingsView.checkBox.stateChanged.connect(self.glWidget.transform.setBox)


        self.settingsView.checkEgg.stateChanged.connect(self.onCheckEgg)

        self.settingsView._boundsChanged.connect(self.glWidget.transform.setBounds)
        self.glWidget.transform._boundsChanged.connect(self.settingsView.setBounds)

        self.transform._boxChanged.connect(self.settingsView.checkBox.setChecked)


        self.settingsView.checkProj.stateChanged.connect(self.transform.setPerspective)
        self.transform._perspectiveChanged.connect(self.settingsView.checkProj.setChecked)

        self.checkKey.stateChanged.connect(self.keyPanel.setVisible)
        self.checkSettings.stateChanged.connect(self.settingsView.setVisible)

        self.checkSliceView.stateChanged.connect(self.sliceWidget.setVisible)
        self.checkSliceView.stateChanged.connect(self.transform.setShowSlice)

        self.settingsView.checkLoopBounce.stateChanged.connect(self.setLoopBounce)

        self.settingsView._stackUnitsChanged.connect(self.transform.setStackUnits)
        self.transform._stackUnitsChanged.connect(self.settingsView.setStackUnits)

        self.settingsView._frameNumberChanged.connect(self.keyPanel.setFrameNumber)

        self.settingsView.colorCombo.currentIndexChanged.connect(self.onColormapChanged)


        self.settingsView._dirNameChanged.connect(self.keyPanel.setDirName)
        # dataModel._dataSourceChanged.connect(self.dataSourceChanged)
        # dataModel._dataPosChanged.connect(self.sliderTime.setValue)

        self.glWidget._dataModelChanged.connect(self.dataModelChanged)

        self.onColormapChanged(0)

        self.checkSliceView.setChecked(False)

        self.hiddableControls = [self.checkSettings,
                                 self.startButton,self.sliderTime,self.spinTime,
                                 self.checkKey,self.screenshotButton ]

        # self.keyPanel.keyView.setModel(self.keyframes)

    def onColormapChanged(self,index):
        self.glWidget.set_colormap(self.settingsView.colormaps[index])
        self.glWidget.refresh()

        self.sliceWidget.glSliceWidget.set_colormap(self.settingsView.colormaps[index])
        self.sliceWidget.glSliceWidget.refresh()



    def onCheckEgg(self,state):
        if state == QtCore.Qt.Checked:
            self.connectEgg3d()
        else:
            self.egg3d.stop()

    def connectEgg3d(self):
        try:
            self.egg3d.listener._quaternionChanged.connect(self.egg3dQuaternion)
            self.egg3d.listener._zoomChanged.connect(self.egg3dZoom)

            N = 45
            self._quatHist = [Quaternion() for i in range(N)]
            self._quatWeights = np.exp(-2.*np.linspace(0,1,N))
            self._quatWeights *= 1./sum(self._quatWeights)
            self.egg3d.start()
        except Exception as e:
            print e
            self.settingsView.checkEgg.setCheckState(QtCore.Qt.Unchecked)


    def egg3dQuaternion(self,a,b,c,d):
        self._quatHist = np.roll(self._quatHist,1)
        self._quatHist[0] = Quaternion(a,c,b,d)

        q0 = Quaternion(0,0,0,0)
        for q,w in zip(self._quatHist,self._quatWeights):
            q0 = q0+q*w

        self.transform.setQuaternion(q0)

    def egg3dZoom(self,zoom):
        if zoom>0:
            newZoom = self.transform.zoom * 1.01**zoom
        else:
            newZoom = self.transform.zoom * 1.1**zoom

        newZoom = np.clip(newZoom,.7,3)
        self.transform.setZoom(newZoom)


    def initUI(self):
        pass


    def keyPressEvent(self, event):
        if type(event) == QtGui.QKeyEvent:
            if event.modifiers()== QtCore.Qt.ControlModifier and  event.key() == QtCore.Qt.Key_Q:
                return
        # super(MainWidget,self).keyPressEvent(event)

    def initActions(self):
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+W"), self, self.closeMe)

        # self.exitAction = QtGui.QAction('Quit', self)
        # self.exitAction.setShortcut('Ctrl+Q')
        # self.exitAction.setStatusTip('Exit application')
        # self.exitAction.triggered.connect(self.foo)

    def setModel(self,dataModel):
        self.glWidget.setModel(dataModel)
        self.sliceWidget.setModel(dataModel)


    def dataModelChanged(self):
        logger.info("data Model changed")
        dataModel = self.glWidget.dataModel
        dataModel._dataSourceChanged.connect(self.dataSourceChanged)

        dataModel._dataPosChanged.connect(self.sliderTime.setValue)
        self.sliderTime.valueChanged.connect(self.transform.setPos)

        self.keyPanel.resetModels(self.transform, KeyFrameList())

        self.dataSourceChanged()

    def dataSourceChanged(self):
        self.sliderTime.setRange(0,self.glWidget.dataModel.sizeT()-1)
        self.sliderTime.setValue(0)
        self.spinTime.setRange(0,self.glWidget.dataModel.sizeT()-1)

        self.settingsView.dimensionLabel.setText("Dim: %s"%str(tuple(self.glWidget.dataModel.size()[::-1])))

        if self.myparent:
            self.myparent.setWindowTitle(self.glWidget.dataModel.name())
        else:
            self.setWindowTitle(self.glWidget.dataModel.name())

        self.keyPanel.resetModels(self.transform, KeyFrameList())


        d = self.glWidget.dataModel[self.glWidget.dataModel.pos]
        minMaxMean = (np.amin(d),np.amax(d),np.mean(d))
        self.settingsView.statsLabel.setText("Min:\t%.2f\nMax:\t%.2f \nMean:\t%.2f"%minMaxMean)



    def forward(self,event):
        if self.glWidget.dataModel:
            newpos = (self.glWidget.dataModel.pos+1)%self.glWidget.dataModel.sizeT()
            self.transform.setPos(newpos)

    def backward(self,event):
        if self.glWidget.dataModel:
            newpos = (self.glWidget.dataModel.pos-1)%self.glWidget.dataModel.sizeT()
            self.transform.setPos(newpos)


    def startPlay(self,event):
        if self.playTimer.isActive():
            self.playTimer.stop()
            self.startButton.setIcon(QtGui.QIcon(absPath("images/icon_start.png")))

        else:
            self.playTimer.start()
            self.startButton.setIcon(QtGui.QIcon(absPath("images/icon_pause.png")))


    def screenShot(self):
        fileName = QtGui.QFileDialog.getSaveFileName(self, 'Save screenshot as',
                                                     '.', selectedFilter='*.png')

        if fileName:
            self.glWidget.saveFrame(fileName)


    def setLoopBounce(self,loopBounce):
        #if loopBounce = True, then while playing it should loop back and forth
        self.loopBounce = loopBounce
        self.settingsView.checkLoopBounce.setChecked(loopBounce)


    def playIntervalChanged(self,val):
        if self.playTimer.isActive():
            self.playTimer.stop()
        self.playTimer.setInterval(val)




    def onPlayTimer(self):

        if self.glWidget.dataModel:


            if self.glWidget.dataModel.pos == self.glWidget.dataModel.sizeT()-1:
                self.playDir = 1-2*self.loopBounce
            if self.glWidget.dataModel.pos == 0:
                self.playDir = 1

            newpos = (self.glWidget.dataModel.pos+self.playDir)%self.glWidget.dataModel.sizeT()
            self.transform.setPos(newpos)


    def contextMenuEvent(self,event):
         # create context menu
        popMenu = QtGui.QMenu(self)
        action = QtGui.QAction('toggle controls', self)
        action.triggered.connect(self.toggleControls)
        popMenu.addAction(action)
        popMenu.setStyleSheet("background-color: white")
        # popMenu.exec_(QtGui.QCursor.pos())


    def toggleControls(self):
        for c in self.hiddableControls:
            c.setVisible(not c.isVisible())

    def closeMe(self):
        #little workaround as on MAC ctrl-q cannot be overwritten

        self.isCloseFlag = True
        self.close()

    def closeEvent(self,event):
        logger.debug("closeevent")
        if not event.spontaneous() and not self.isCloseFlag:
            event.ignore()
        else:
            if self.playTimer.isActive():
                self.playTimer.stop()

            if self.rotateTimer.isActive():
                self.rotateTimer.stop()

            # self.glWidget.setParent(None)
            # del self.glWidget
            event.accept()


    def center(self):
        self.transform.center()

    def rotate(self):
        if self.rotateTimer.isActive():
            self.rotateTimer.stop()
            self.rotateButton.setIcon(QtGui.QIcon(absPath("images/icon_rotate.png")))

        else:
            self.rotateTimer.start()
            self.rotateButton.setIcon(QtGui.QIcon(absPath("images/icon_rotate_active.png")))


    def onRotateTimer(self):
        self.transform.addRotation(-.02,0,1.,0)
        self.glWidget.render()
        self.glWidget.updateGL()

    def mouseDoubleClickEvent(self,event):
        super(MainWidget,self).mouseDoubleClickEvent(event)
        if self.isFullScreen:
            self.showNormal()
        else:
            self.showFullScreen()

        self.glWidget.resized = True

        # there's a bug in Qt that disables drop after fullscreen, so reset it...
        self.setAcceptDrops(True)

        self.isFullScreen = not self.isFullScreen




if __name__ == '__main__':
    import argparse

    app = QtGui.QApplication(sys.argv)

    win = MainWidget()

    win.setModel(DataModel(DemoData()))

    # win.setModel(DataModel(TiffData("/Users/mweigert/Data/droso_test.tif")))

    win.show()
    win.raise_()

    sys.exit(app.exec_())
