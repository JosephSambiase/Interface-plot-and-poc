import os, sys
import numpy as np
import glob
from constants import *
from jpk.loadjpkfile import loadJPKfile
from jpk.loadjpkthermalfile import loadJPKThermalFile
from nanosc.loadnanoscfile import loadNANOSCfile
from load_uff import loadUFFtxt
from uff import UFF
import matplotlib.pyplot as plt
from pyafmrheo.utils.force_curves import *
from pyafmrheo.models.hertz import HertzModel

# interface

from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QPushButton, QHBoxLayout, QWidget, QMessageBox
from pyafmreader import loadfile
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Set up the main window
        self.setWindowTitle('Plotting datas')
        self.setFixedSize(1280,720)
        # Add a menu bar
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu('File')
        

        # Add a "Open" action to the File menu
        open_action = file_menu.addAction('Open a file')
        open_action.triggered.connect(self.open_file)
        
        plot_action = file_menu.addAction('Plot deflection vs height')
        plot_action.triggered.connect(self.plot_data)
        
        analyze_action = file_menu.addAction('Plot the point of contact')
        analyze_action.triggered.connect(self.calculate_poc)
        
        folder_action = file_menu.addAction('Open a folder')
        folder_action.triggered.connect(self.open_folder)
        
        force_action = file_menu.addAction('Plot force vs indentation')
        force_action.triggered.connect(self.plot_force)
        
        self.define_buttons()
        self.plot_button.clicked.connect(self.plot_data)
        
        
        
        
        
    
    def define_buttons(self):
        hbox = QHBoxLayout()
        self.central_widget = QWidget()
        self.central_widget.setLayout(hbox)
        self.setCentralWidget(self.central_widget)
        self.plot_button = QPushButton('Plot')
        self.layout = QHBoxLayout()
        self.layout.addWidget(self.plot_button)
        hbox.addWidget(self.plot_button)
        


    def open_file(self):
        # Show a file dialog to select a file
        filename, _ = QFileDialog.getOpenFileName(self, 'Open File', '', 'All files (*.*)')
        self.file = self.loadfile(filename)

    def open_folder(self):
        dirname = QFileDialog.getExistingDirectory(
				self, 'Choose Directory', r'./'
			)
        if dirname != "" and dirname is not None:
            valid_files = self.getFileList(dirname)
            if valid_files != []:
                for filename in glob.glob(os.path.join(dirname, '*.jpk-force')):
                    print (filename)
                    self.file = self.loadfile(filename)
                    self.collectData()
                    self.plot_force()
                
                    
                    
    def collectData(self):
        self.deflection_sensitivity = None # m/V
        # If None it will use the spring constant from the file
        self.spring_constant = None # N/m
        self.filemetadata = self.file.filemetadata
        self.closed_loop = self.filemetadata['z_closed_loop']
        self.file_deflection_sensitivity = self.filemetadata['defl_sens_nmbyV'] #nm/V
        self.file_spring_constant = self.filemetadata['spring_const_Nbym'] #N/m
        self.height_channel = self.filemetadata['height_channel_key']

        if not self.deflection_sensitivity: self.deflection_sensitivity = self.file_deflection_sensitivity / 1e9 #m/V
        if not self.spring_constant: self.spring_constant = self.file_spring_constant

        self.curve_idx = 0
        self.force_curve = self.file.getcurve(self.curve_idx)
        self.extend_segments = self.force_curve.extend_segments
        self.pause_segments = self.force_curve.pause_segments
        self.modulation_segments = self.force_curve.modulation_segments
        self.retract_segments = self.force_curve.retract_segments
        self.force_curve_segments = self.force_curve.get_segments()
        first_exted_seg_id, self.first_ext_seg = self.extend_segments[0]
        self.first_ext_seg.preprocess_segment(self.deflection_sensitivity, self.height_channel)
        last_ret_seg_id, last_ret_seg = self.retract_segments[-1]
        last_ret_seg.preprocess_segment(self.deflection_sensitivity, self.height_channel)
        xzero = last_ret_seg.zheight[-1] # Maximum height
        self.first_ext_seg.zheight = xzero - self.first_ext_seg.zheight
        last_ret_seg.zheight = xzero - last_ret_seg.zheight
        app_height = self.first_ext_seg.zheight
        app_deflection = self.first_ext_seg.vdeflection
        ret_height = last_ret_seg.zheight
        ret_deflection = last_ret_seg.vdeflection
        #define pt of contact
        self.poc = get_poc_RoV_method(app_height, app_deflection, 350e-9)

                    
                    
                    
    

    def getFileList(self, directory):
        types = ('*.jpk-force', '*.jpk-force-map', '*.jpk-qi-data', '*.jpk-force.zip', '*.jpk-force-map.zip', '*.jpk-qi-data.zip', '*.spm', '*.pfc')
        dataset_files = []
        for files in types:
            dataset_files.extend(glob.glob(f'{directory}/**/{files}', recursive=True))
        return dataset_files
    
    def loadfile(self, filepath):
        split_path = filepath.split(os.extsep)
        if os.name == 'nt' and split_path[-1] == '.zip':
            filesuffix = split_path[-2]
        else:
            filesuffix = split_path[-1]
    
        uffobj = UFF()
    
        if filesuffix[1:].isdigit() or filesuffix in nanoscfiles:
            return loadNANOSCfile(filepath, uffobj)
    
        elif filesuffix in jpkfiles:
            return loadJPKfile(filepath, uffobj, filesuffix)
        
        elif filesuffix in ufffiles:
            return loadUFFtxt(filepath, uffobj)
        
        elif filesuffix in jpkthermalfiles:
            return loadJPKThermalFile(filepath)

        
    def plot_data(self):
        # Shapes available: paraboloid, pyramid
        # indenter_shape = "paraboloid"
        # tip_parameter = 30 * 1e-9 # meters
        # Poisson ratio
        # poisson_ratio = 0.5
        # Max non contact region
        # maxnoncontact = 2.5 * 1e-6
        # Window to find cp
        # windowforCP = 70 * 1e-9
        # Smooth window
        # smooth_w = 1
        # t0 scaling factor
        # t0_scaling = 1
        # Viscous drag for PFQNM
        # vdrag = 0.77*1e-6
        # If None it will use the deflection sensitivity from the file
        self.deflection_sensitivity = None # m/V
        # If None it will use the spring constant from the file
        self.spring_constant = None # N/m
        self.filemetadata = self.file.filemetadata
        self.closed_loop = self.filemetadata['z_closed_loop']
        self.file_deflection_sensitivity = self.filemetadata['defl_sens_nmbyV'] #nm/V
        self.file_spring_constant = self.filemetadata['spring_const_Nbym'] #N/m
        self.height_channel = self.filemetadata['height_channel_key']

        if not self.deflection_sensitivity: self.deflection_sensitivity = self.file_deflection_sensitivity / 1e9 #m/V
        if not self.spring_constant: self.spring_constant = self.file_spring_constant

        self.curve_idx = 0
        self.force_curve = self.file.getcurve(self.curve_idx)
        self.extend_segments = self.force_curve.extend_segments
        self.pause_segments = self.force_curve.pause_segments
        self.modulation_segments = self.force_curve.modulation_segments
        self.retract_segments = self.force_curve.retract_segments
        self.force_curve_segments = self.force_curve.get_segments()
        
        
        self.graphWidget = pg.PlotWidget()
        self.setCentralWidget(self.graphWidget)
        self.graphWidget.setBackground('w')
        
        
        colors = [ (0, 0, 255),(255, 128, 0)] # define orange and blue colors
        for i, (seg_id, segment) in enumerate(self.force_curve_segments):
            height = segment.segment_formated_data[self.height_channel]
            deflection = segment.segment_formated_data["vDeflection"]
            pen = pg.mkPen(color=colors[i%len(colors)]) # set the color based on index
            self.graphWidget.plot(height, deflection, pen=pen)
        styles = {'color':'k', 'font-size':'20px'}
        self.graphWidget.setLabel('left', 'vDeflection [Volts]',**styles)
        self.graphWidget.setLabel('bottom', 'Piezo Height [Meters]',**styles)

        

        
        # t0 = 0
        # for seg_id, segment in self.force_curve_segments:
        #     deflection = segment.segment_formated_data["vDeflection"]
        #     time = segment.segment_formated_data["time"] + t0
        #     plt.plot(time, deflection)
        #     t0 = time[-1]
        # plt.xlabel("Time [s]")
        # plt.ylabel("Deflection [Volts]")
        # plt.grid()
        # plt.show()
        
    def plot_force(self):
        # self.poc[1] = 0
        self.first_ext_seg.get_force_vs_indentation(self.poc, self.spring_constant)
        app_indentation, app_force = self.first_ext_seg.indentation, self.first_ext_seg.force
        #hertz_d0 = HertzModel.d0
        pen = pg.mkPen(color=(0, 0, 255))
        if not hasattr(self, 'graphWidget'):
            self.graphWidget = pg.PlotWidget()
            self.setCentralWidget(self.graphWidget)
            self.graphWidget.setBackground('w')
            vori=pg.InfiniteLine(0, angle=90)
            hori=pg.InfiniteLine(0, angle=0)
            self.graphWidget.addItem(vori)
            self.graphWidget.addItem(hori)
    
        self.graphWidget.plot(app_indentation, app_force, pen=pen)
        
        styles = {'color':'k', 'font-size':'20px'}
        self.graphWidget.setLabel('left', 'Force [Newton]',**styles)
        self.graphWidget.setLabel('bottom', 'Indentation [Meters]',**styles)
    
    

        
    def calculate_poc(self):
        
        
        first_exted_seg_id, self.first_ext_seg = self.extend_segments[0]

        self.first_ext_seg.preprocess_segment(self.deflection_sensitivity, self.height_channel)

        last_ret_seg_id, last_ret_seg = self.retract_segments[-1]
        last_ret_seg.preprocess_segment(self.deflection_sensitivity, self.height_channel)
   
        xzero = last_ret_seg.zheight[-1] # Maximum height
        self.first_ext_seg.zheight = xzero - self.first_ext_seg.zheight
        last_ret_seg.zheight = xzero - last_ret_seg.zheight

        app_height = self.first_ext_seg.zheight
        app_deflection = self.first_ext_seg.vdeflection
        ret_height = last_ret_seg.zheight
        ret_deflection = last_ret_seg.vdeflection
        
        self.poc = get_poc_RoV_method(app_height, app_deflection, 350e-9)
    
        
        pen = pg.mkPen(color=(0, 0, 255))
        pen2 = pg.mkPen(color=(255, 128, 0))
        pen3 = pg.mkPen(color=(255, 0, 0))
        
        
        self.graphWidget = pg.PlotWidget()
        self.setCentralWidget(self.graphWidget) 
        self.graphWidget.setBackground('w')
        
        self.graphWidget.plot(app_height, app_deflection, pen=pen)
        self.graphWidget.plot(ret_height, ret_deflection, pen=pen2)
        vLine=pg.InfiniteLine(pos=self.poc[0], angle=90, pen=pen3)
        self.graphWidget.addItem(vLine)
        hLine=pg.InfiniteLine(pos=self.poc[1], angle=0, pen=pen3)
        self.graphWidget.addItem(hLine)
    
        # display poc coordinates
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Point of contact coordinates")
        dlg.setText("x: " + str(self.poc[0])+ ", y: " + str(self.poc[1]))
        dlg.exec()        
       

        

     
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

