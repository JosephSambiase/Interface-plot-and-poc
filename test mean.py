# Import used for the functions
import os, sys
import numpy as np
import glob
from constants import *
from jpk.loadjpkfile import loadJPKfile
from jpk.loadjpkthermalfile import loadJPKThermalFile
from nanosc.loadnanoscfile import loadNANOSCfile
from load_uff import loadUFFtxt
from uff import UFF
from pyafmrheo.utils.force_curves import *
import numpy as np
import matplotlib.pyplot as plt


# Import used for the interface
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QPushButton, QHBoxLayout, QWidget, QMessageBox
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
        
        # Add a "Plot deflection vs height" action to the File menu
        plot_action = file_menu.addAction('Plot deflection vs height')
        plot_action.triggered.connect(self.plot_data)
        
        # Add a "Plot PoC" action to the File menu
        analyze_action = file_menu.addAction('Plot the point of contact')
        analyze_action.triggered.connect(self.calculate_poc)
        
        # Add a "Plot force vs indentation" action to the File menu 
        force_action = file_menu.addAction('Plot force vs indentation')
        force_action.triggered.connect(self.plot_force)
        
        # Add a "Open" action to the File menu
        folder_action = file_menu.addAction('Open a folder + plot force vs indentation')
        folder_action.triggered.connect(self.open_folder)
        
        # Activate the button plot in the center of the window
        self.define_buttons()
        self.plot_button.clicked.connect(self.plot_data)
        
        
    # Define the button plot in the center of the window
    def define_buttons(self):
        hbox = QHBoxLayout()
        self.central_widget = QWidget()
        self.central_widget.setLayout(hbox)
        self.setCentralWidget(self.central_widget)
        self.plot_button = QPushButton('Plot')
        self.layout = QHBoxLayout()
        self.layout.addWidget(self.plot_button)
        hbox.addWidget(self.plot_button)
        

    # Function used to open a file 
    def open_file(self):

        # Show a file dialog to select a file
        filename, _ = QFileDialog.getOpenFileName(self, 'Open File', '', 'All files (*.*)')
        self.file = self.loadfile(filename)


    # Function used to open a folder
    def open_folder(self):
        dirname = QFileDialog.getExistingDirectory(
				self, 'Choose Directory', r'./'
			)
        if dirname != "" and dirname is not None:
            valid_files = self.getFileList(dirname)
            if valid_files != []:
                indentation = []
                k=0
                for filename in glob.glob(os.path.join(dirname, '*.jpk-force')):                  
                    self.file = self.loadfile(filename)
                    self.collectData()
                    self.plot_force()    
                    k=k+1
                    
                    bin_size = 10e-9 # Set the bin size
                    n_bins = int(max(self.app_force) / bin_size) + 1  # Calculate the number of bins
                    print(n_bins)
                    
                    for i in range(n_bins+1):
                        lower_limit = i * bin_size
                        upper_limit = (i + 1) * bin_size
                        mask = (self.app_force >= lower_limit) & (self.app_force < upper_limit) & (self.app_indentation >= 0)
                        indent_range = self.app_indentation[mask]
                        indentation.append(indent_range)
              
                #Pour 2 fichiers, moyenne de 0 a 10 nN :
                
                # sum_indentation=sum(indentation[0])+sum(indentation[46])
                # print(sum_indentation)
                # mean_indentation=sum_indentation/(len(indentation[0])+len(indentation[46]))
                # print(mean_indentation)
                
                
                #Pour k fichiers, moyenne de 0 a 10 nN :
                    
                # mean_indentation=[]
                # s=0
                # l=0    
                # for i in range(k):
                #     s+=sum(indentation[i*n_bins])
                #     l+=len(indentation[i*n_bins])
                # mean_indentation.append(s/l)
                # print(mean_indentation)
                
   
                indentation = np.array(indentation)
                indentation = np.array_split(indentation, k)
                           
                list_mean = []
                for i in range (k):
                    for j in range(n_bins):
                        arr = np.array(indentation[i][j])
                        list_mean.append(np.mean(arr))
              
                
                list_mean=np.array(list_mean)
                list_mean=np.array_split(list_mean, k)
                
                sum_mean=[]
                for i in range(n_bins):
                    s=0
                    for j in range(k):
                        s+=list_mean[j][i]
                    sum_mean.append(s)
                
                mean_indentation = [x / k for x in sum_mean]
                print(mean_indentation)
                    
                
                        
                        
                        
                
                
                
                
                
                # list_mean = np.array(list_mean)
                # list_mean2 = []
                # for i in range (k+1):
                #     for j in range(n_bins+1):
                #         list_mean[i][j]
                    
                        
                
                
                
                
                    
                 
                    
                 
                    
                 
                    
                 
                    
                    # x = np.arange(bin_size / 2, n_bins * bin_size, bin_size)  # X-axis values for the error bars
                    # y = mean_indentation  # Y-axis values
                    
                    
           
                
 
    # Function used to collect datas needed to plot the force vs indentation
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
        # Define poc
        self.poc = get_poc_RoV_method(app_height, app_deflection, 700e-9)

    
    # Function used in the opening of a folder
    def getFileList(self, directory):
        types = ('*.jpk-force', '*.jpk-force-map', '*.jpk-qi-data', '*.jpk-force.zip', '*.jpk-force-map.zip', '*.jpk-qi-data.zip', '*.spm', '*.pfc')
        dataset_files = []
        for files in types:
            dataset_files.extend(glob.glob(f'{directory}/**/{files}', recursive=True))
        return dataset_files
  
    
    # Function used to read the .jpk-force files
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

        
    # Function used to plot the deflection vs the height for a file
    def plot_data(self):
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

        
    # Function used to plot the force vs the indentation for a folder 
    def plot_force(self):
        self.first_ext_seg.get_force_vs_indentation(self.poc, self.spring_constant)
        self.app_indentation, self.app_force = self.first_ext_seg.indentation, self.first_ext_seg.force
        pen = pg.mkPen(color=(0, 0, 255))
        if not hasattr(self, 'graphWidget'):
            self.graphWidget = pg.PlotWidget()
            self.setCentralWidget(self.graphWidget)
            self.graphWidget.setBackground('w')
 
        self.graphWidget.plot(self.app_indentation-self.poc[0], self.app_force-self.poc[1], pen=pen)
        styles = {'color':'k', 'font-size':'20px'}
        self.graphWidget.setLabel('left', 'Force [Newton]',**styles)
        self.graphWidget.setLabel('bottom', 'Indentation [Meters]',**styles)
    
    
    # Function used to plot and give the coordinates of the PoC    
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
    
        # Display poc coordinates
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Point of contact coordinates")
        dlg.setText("x: " + str(self.poc[0])+ ", y: " + str(self.poc[1]))
        dlg.exec()        
      
     
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

