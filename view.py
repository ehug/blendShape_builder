'''
# ================================================================================================ #
BlendShape Builder
Purpose: To create corrective Blendhspaes targets for blendshape nodes

Dependencies:
            maya
            OpenMayaUI
            PySide2 / PySide6

Author: Eric Hug

Updated: 12/31/2024

# Code:
from importlib import reload
from blendShape_builder import view
reload(view)
view.start_up()
'''
# ================================================================================================ #
# IMPORT
import logging
from importlib import reload

from maya import cmds, OpenMayaUI
try:
    from PySide6 import QtWidgets, QtCore, QtGui
    from PySide6.QtGui import QAction
    from shiboken6 import wrapInstance
except:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtWidgets import QAction
    from shiboken2 import wrapInstance

from blendShape_builder import core
reload(core)

# ================================================================================================ #
# VARIABLES
LOG = logging.getLogger(__name__)
MENUBAR_STYLESHEET_ACTIVE = '''
QMenuBar {
    background: rgb(55,55,55);
    color: lightgrey;
}
'''

# ================================================================================================ #
# FUNCTIONS
def start_up(width=600, height=200):
    '''Start Function for user to run the tool.'''
    win = get_maya_main_window()
    for each in win.findChildren(QtWidgets.QWidget):
        if each.objectName() == "BlendShapeBuilder":
            each.deleteLater()
    tool = BlendShapeBuilder(parent=win)
    tool.resize(width, height)
    tool.show()

    return tool

def get_maya_main_window():
    '''Locates Main Window, so we can parent our tool to it.'''
    maya_window_ptr = OpenMayaUI.MQtUtil.mainWindow()

    return wrapInstance(int(maya_window_ptr), QtWidgets.QWidget)

#==================================================================================================#
# CLASSES
class BlendShapeBuilder(QtWidgets.QWidget):
    """
    Purpose:
       This tool is used in Maya to create BlendShape-Targets from sculpted meshes for 
       a BlendShape Node in an efficient manner.
    """

    def __init__(self, parent=None):
        super(BlendShapeBuilder, self).__init__(parent=parent)
        self.search_type = "files"
        self.file_types = "Mesh Files (*.obj *.fbx *.mb *.ma);;"
        # =========== #
        # Base Window #
        # =========== #
        self.setWindowTitle("BlendShapeBuilder")
        self.setObjectName("BlendShapeBuilder")
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setSpacing(6)
        self.main_layout.setContentsMargins(QtCore.QMargins(0, 0, 0, 0))
        self.setLayout(self.main_layout)
        self.main_layout.setAlignment(QtCore.Qt.AlignTop)
        self.components_widget = BasicWidget(layout_type="vertical", 
                                             spacing=6, 
                                             margins=[9,0,9,9])
        # ========== #
        # Components #
        # ========== #
        # ----- #
        # Menus #
        # ----- #
        self.menu_bar = QtWidgets.QMenuBar()
        self.menu = QtWidgets.QMenu("File")
        self.menu_actions = [QAction("Tool Instructions"), 
                             QAction("Import Mesh(s)")]
        self.menu_bar.addMenu(self.menu)
        for each in self.menu_actions:
            self.menu.addAction(each)
        self.menu_actions[0].triggered.connect(self.display_instructions)
        self.menu_actions[1].triggered.connect(self.import_mesh)
        # Component Settings #
        self.menu_bar.setStyleSheet(MENUBAR_STYLESHEET_ACTIVE)

        # ---------------------------- #
        # Select BlendShape Node Field #
        # ---------------------------- #
        self.bs_node_widget = SelectionWidget(label_text="BlendShape Node:", btn_text="Select")

        # ------------------ #
        # BlendShape Options #
        # ------------------ #
        self.options_widget   = BasicWidget(spacing=6)
        self.btn_widget       = BasicWidget(layout_type="horizontal", spacing=6)
        self.bs_type_label    = QtWidgets.QLabel("BlendShape Type:")
        self.regular_rbtn     = QtWidgets.QRadioButton("Regular BlendShape")
        self.combination_rbtn = QtWidgets.QRadioButton("Combination BlendShape")
        self.options_separator = QtWidgets.QFrame()
        # Component Settings #
        self.regular_rbtn.setChecked(True)
        self.options_separator.setLineWidth(1)
        self.options_separator.setFrameShape(QtWidgets.QFrame.HLine)
        # Assemble Component #
        self.btn_widget.layout.addWidget(self.regular_rbtn)
        self.btn_widget.layout.addWidget(self.combination_rbtn)
        self.options_widget.layout.addWidget(self.bs_type_label)
        self.options_widget.layout.addWidget(self.btn_widget)

        # ------------------------ #
        # Create BlendShape Target #
        # ------------------------ #
        self.create_widget = BasicWidget(layout_type="horizontal", spacing=6)
        self.create_btn = QtWidgets.QPushButton("Create Target")
        self.create_widget.layout.setAlignment(QtCore.Qt.AlignRight)
        # Component Settings #
        self.create_btn.clicked.connect(self.create)
        self.create_btn.setFixedWidth(110)
        self.create_btn.setFixedHeight(55)
        # Assemble Component #
        self.create_widget.layout.addWidget(self.create_btn)
        
        # =================== #
        # Assemble Components #
        # =================== #
        self.main_layout.addWidget(self.menu_bar)
        self.main_layout.addWidget(self.components_widget)
        self.components_widget.layout.addWidget(self.bs_node_widget)
        self.components_widget.layout.addWidget(self.options_widget)
        self.components_widget.layout.addWidget(self.options_separator)
        self.components_widget.layout.addWidget(self.create_widget)

        # ======== #
        # Finalize #
        # ======== #
        self.setWindowFlags(QtCore.Qt.Window)

    def create(self):
        '''Create the BlendShape target'''
        bs_node = self.bs_node_widget.textfield.text()
        src_geo = cmds.listConnections("{}.originalGeometry[0]".format(bs_node))
        sculpted_mesh = cmds.ls(selection=True, exactType="transform")
        # Check for invalid data
        if bs_node == "":
            LOG.error("BlendShape Node not Specified. Please enter node name in textfield.")
        elif cmds.objExists(bs_node) == False:
            LOG.error("Blendshape Node \"{}\" was not found in scene. Check that entered name is spelled correct.".format(bs_node))
        elif len(src_geo) == 0:
            LOG.error("No source geometry found connected to blendShape node's attribute \"originalGeometry[0]\".")
        elif len(sculpted_mesh) == 0:
            LOG.error("Please have Sculpted Geometry selected to create blendShape target.")
        elif cmds.polyEvaluate(src_geo[0], vertex=True) != cmds.polyEvaluate(sculpted_mesh[0], vertex=True):
            LOG.error("Source Mesh and Sculpted Mesh do not have the same number of vertices.")
        # Create BlendShape
        if self.regular_rbtn.isChecked():
            core.create_regular_corrective(src_mesh        = src_geo[0], 
                                           sculpted_mesh   = sculpted_mesh[0],
                                           blendshape_node = bs_node)
        else:
            core.create_combination_corrective(src_mesh        = src_geo[0], 
                                               sculpted_mesh   = sculpted_mesh[0], 
                                               blendshape_node = bs_node)
            
    def import_mesh(self):
        '''Import blendshape mesh and frame in viewport'''
        # Get file path
        file_path = self.browse_command()
        if len(file_path) == 0:
            LOG.error("No mesh file was selected. Import cancelled.")
            return
        else:
            file_path = file_path.replace("\'", "")

        file_paths = []
        if "," in file_path:
            file_paths = file_path.replace(" ", "")
            file_paths = file_paths.split(",")
        else:
            file_paths = [file_path]
        for each in file_paths:
            mesh_name = each.split("/")[-1].split(".")[0]
            if cmds.objExists(mesh_name):
                cmds.delete(mesh_name)
            # Import file
            mesh = core.import_src_mesh(file_path=each).split("|")[-1]
            if mesh != mesh_name:
                cmds.rename(mesh, mesh_name)

    def browse_command(self):
        '''When Browse Button pressed, allows user to select a folder,
           and returns folder path into textfield.
        '''
        # Determine Search Type
        if self.search_type == "saveFile":
            self.sel_file = QtWidgets.QFileDialog.getSaveFileName(self,
                                                                  caption="save file",
                                                                  filter=self.file_types)
        elif self.search_type == "file":
            self.sel_file = QtWidgets.QFileDialog.getOpenFileName(self,
                                                                  caption="get file",
                                                                  filter=self.file_types)
        elif self.search_type == "files":
            self.sel_file = QtWidgets.QFileDialog.getOpenFileNames(self,
                                                                   caption="get files",
                                                                   filter=self.file_types)
        elif self.search_type == "directory":
            self.sel_file = QtWidgets.QFileDialog.getExistingDirectory(self,
                                                                       caption="Choose Directory",
                                                                       options=QtWidgets.QFileDialog.ShowDirsOnly)
        else:
            LOG.error("Invalid argument \'{}\' for parameter: \'search_type\'."
                      "\nValid options: \'file\', \'files\', \'directory\'".format(self.search_type))

        # Return path to textfield
        if isinstance(self.sel_file, tuple):
            # Use for 'file' or 'files'
            new_string = list(self.sel_file)
            new_string.pop(-1)
            new_string = str(new_string).replace("[", "").replace("]", "")
            

        return new_string
    
    def display_instructions(self):
        '''Creates Popup Window with an explanation for how to use the tool'''
        instructions_popup = InstructionsWidget(self)
        main_window = self
        instructions_popup.move(main_window.width()+main_window.x(), main_window.y()) # Put window next to tool's main ui
        instructions_popup.resize(0,0) # Shrink window to smallest size possible
        instructions_popup.show()

        return instructions_popup
            

class SelectionWidget(QtWidgets.QWidget):
    """
    Purpose:
       Reuseable widget for displaying selected object in a textfield for other tools to draw from
    Parameters:
                parent     : The parent widget to attach this widget to. 
                                        Helpful for connecting widget to an application's main window, like Maya. 
                                        Otherwise, leave as None.
                label_text : Text that appears to the left of the textfield
                btn_text   : Text that appears on the button to the right of the textfield
       
    """
    def __init__(self, parent=None, label_text="", btn_text=""):
        super(SelectionWidget, self).__init__(parent=parent)
        # ========== #
        # Parameters #
        # ========== #
        self.label_text = label_text
        self.btn_text   = btn_text
        # =========== #
        # Base Window #
        # =========== #
        self.main_layout = QtWidgets.QHBoxLayout()
        self.main_layout.setSpacing(6)
        self.main_layout.setContentsMargins(QtCore.QMargins(0, 0, 0, 0))
        self.setLayout(self.main_layout)
        # ========== #
        # Components #
        # ========== #
        self.label = QtWidgets.QLabel(self.label_text)
        self.textfield = QtWidgets.QLineEdit()
        self.btn = QtWidgets.QPushButton(self.btn_text)
        # Component Settings #
        self.textfield.setFixedHeight(35)
        self.btn.setFixedHeight(35)
        self.btn.setFixedWidth(110)
        self.btn.clicked.connect(self.get_selection)

        # =================== #
        # Assemble Components #
        # =================== #
        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.textfield)
        self.main_layout.addWidget(self.btn)

    def get_selection(self):
        sel = cmds.ls(selection=True)[0]
        self.textfield.setText(sel)

class BasicWidget(QtWidgets.QWidget):
    def __init__(self, parent=None, layout_type="vertical", spacing=0, margins=[0,0,0,0], h_align="left", v_align="top"):
        '''Creates a widget that acts a base template for other tools to build from.
            Parameters:
                        parent:      The parent widget to attach this widget to. 
                                        Helpful for connecting widget to an application's main window, like Maya. 
                                        Otherwise, leave as None.
                        layout_type: How items are place in the widget's layout.
                                        values: "vertical", "horizontal", "grid"
                        spacing:     Space between other UI components inside this widget.

                        margins:     Border space around all for sides of the widget. 
                                        [left, top, right, bottom]
                        h_align:     Horizontal alignment of items.
                                        values: "left", "center", "right"
                        v_align:     Vertical alignment of items. 
                                        values: "top", "center", "bottom"
        '''
        super(BasicWidget, self).__init__(parent=parent)
        self.layout_type = layout_type
        self.h_align = h_align
        self.v_align = v_align
        self.spacing = spacing
        self.margins = QtCore.QMargins(margins[0], margins[1], margins[2], margins[3])
        
        # Base Window
        # # Layout Type
        self.layout = QtWidgets.QVBoxLayout()
        if self.layout_type == "vertical":
            self.layout = QtWidgets.QVBoxLayout()
        elif self.layout_type == "horizontal":
            self.layout = QtWidgets.QHBoxLayout()
        elif self.layout_type == "grid":
            self.layout = QtWidgets.QGridLayout()
        else:
            LOG.error("Invalid Layout Argument: \'{}\'".format(self.layout_type))
        self.setLayout(self.layout)
        # # Layout Alignments:
        # # # Horizontal
        if self.h_align == "left":
            self.layout.setAlignment(QtCore.Qt.AlignLeft)
        elif self.h_align == "center":
            self.layout.setAlignment(QtCore.Qt.AlignHCenter)
        elif self.h_align == "right":
            self.layout.setAlignment(QtCore.Qt.AlignRight)
            print(self.h_align)
        else:
            LOG.error("Invalid Horizontal Alignment Argument (\'h_align\'): \'{}\'".format(self.h_align))
        # # # Vertical
        if self.v_align == "top":
            self.layout.setAlignment(QtCore.Qt.AlignTop)
        elif self.v_align == "center":
            self.layout.setAlignment(QtCore.Qt.AlignVCenter)
        elif self.v_align == "bottom":
            self.layout.setAlignment(QtCore.Qt.AlignBottom)
        else:
            LOG.error("Invalid Vertical Alignment Argument (\'v_align\'): \'{}\'".format(self.v_align))
        # # Spacing
        self.layout.setSpacing(self.spacing)
        self.layout.setContentsMargins(self.margins)

class InstructionsWidget(QtWidgets.QDialog):
    def __init__(self, parent=None):
        '''Creates a widget with instructions on how to use the main tool.
        '''
        super(InstructionsWidget, self).__init__(parent=parent)
        self.instructions = """Step 1: Import your sculpted corrected meshes.\n
Step 2: Select the skinned mesh and select the BlendShape Node in question (leave blendshape active).\n
Step 3: Press the \"Select\" button to confirm the blendshape node.\n
Step 4: Pose your skinned mesh.\n
Step 5: Select only your sculpted mesh (and only the sculpted mesh).\n
Step 6: Choose your target type (regular or combination) and then press \"Create Target\"."""
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setAlignment(QtCore.Qt.AlignTop)
        self.main_layout.setSpacing(6)
        self.main_layout.setContentsMargins(6, 6, 6, 6)
        self.setLayout(self.main_layout)
        self.instructions_label = QtWidgets.QLabel(self.instructions)
        self.main_layout.addWidget(self.instructions_label)
        self.setWindowModality(QtCore.Qt.NonModal)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowTitle('BlendShape Builder Instructions')

