'''
# ================================================================================================ #
BlendShape Builder

Purpose: Creating Blendshapes from models sculpted from another program like ZBrush

Dependencies:

Author: Eric Hug

Updated: 12/31/2024

'''
# ================================================================================================ #
# IMPORTS
import logging

from maya import cmds, mel

# ================================================================================================ #
# VARIABLES
LOG = logging.getLogger(__name__)

# ================================================================================================ #
# FUNCTIONS
def import_src_mesh(file_path=""):
    '''Imports the specified obj file and returns the name of the mesh without any namespace
        Parameters:
                    file_path: full file path of the specified mesh
    '''
    mesh_name = ""
    nodes = cmds.file(file_path, 
                      i=True, 
                      force=True,
                      groupReference=False, 
                      mergeNamespacesOnClash=True,
                      removeDuplicateNetworks=True,
                      returnNewNodes=True)
    for each in nodes:
        if cmds.nodeType(each) == "transform":
            mesh_name = each
            break

    return mesh_name

def create_corrective_blendshape_mesh(src_mesh="", sculpted_mesh=""):
    '''Create a corrective blendshape mesh that can be correctly used as a blendshape target
    Parameters:
                src_mesh      : Default posed mesh without any blendshapes or other deformers besides skinCluster being active.
                sculpted_mesh : Sculpted mesh into correct pose.
    '''
    if src_mesh=="" or sculpted_mesh=="":
        sel = cmds.ls(selection=True)
        if len(sel) == 2:
            src_mesh = sel[0]
            sculpted_mesh = sel[1]
        else:
            LOG.error("Corrective Blendshape not created. Make sure to have two meshes selected. No more. No less.")
    new_shape = cmds.invertShape(src_mesh, sculpted_mesh)
    cmds.sets(new_shape, edit=True, forceElement="initialShadingGroup")

    return new_shape

def create_regular_corrective(src_mesh="", sculpted_mesh="", blendshape_node=""):
    '''Create a corrective Combination blendshape mesh that can be correctly used as a blendshape target
    Parameters:
                src_mesh        : Default posed mesh without any blendshapes or other deformers besides skinCluster being active.
                sculpted_mesh   : Sculpted mesh into correct pose.
                blendshape_node : Blendshape node the combination shape will be added to
    '''
    # Turn off blendShape node temporarily
    cmds.setAttr("{}.envelope".format(blendshape_node), 0) # temporarily turn off blendshape node to get correct inverted shape
    # Create the inverted shape
    inverted_shape = create_corrective_blendshape_mesh(src_mesh=src_mesh, 
                                                       sculpted_mesh=sculpted_mesh)
    # Get all blendshape targets and designated target number
    highest_target_number = 0 # Our new combination blendshape target's number will be highest + 1
    total_targets = cmds.aliasAttr(blendshape_node, query=True)
    if total_targets != None:
        targets_dict = {}
        for num in range(0, len(total_targets), 2):
            target_name = total_targets[num]
            targets_dict[target_name] = int(total_targets[num+1].replace("weight[","").replace("]",""))
            if targets_dict[target_name] > highest_target_number:
                highest_target_number = targets_dict[target_name]
        highest_target_number += 1

    # Finalize Combination blendshape and delete leftover data
    cmds.blendShape(blendshape_node, 
                    edit   = True, 
                    target = [src_mesh, highest_target_number, inverted_shape, 1], 
                    weight = [highest_target_number, 0])
    cmds.setAttr("{}.envelope".format(blendshape_node), 1)
    cmds.delete(inverted_shape)
    
def create_combination_corrective(src_mesh="", sculpted_mesh="", blendshape_node=""):
    '''Create a corrective Combination blendshape mesh that can be correctly used as a blendshape target
    Parameters:
                src_mesh        : Default posed mesh without any blendshapes or other deformers besides skinCluster being active.
                sculpted_mesh   : Sculpted mesh into correct pose.
                blendshape_node : Blendshape node the combination shape will be added to
    '''
    # Create the inverted shape
    cmds.setAttr("{}.envelope".format(blendshape_node), 0) # temporarily turn off blendshape node to get correct inverted shape
    inverted_shape = create_corrective_blendshape_mesh(src_mesh=src_mesh, 
                                                       sculpted_mesh=sculpted_mesh)
    cmds.setAttr("{}.envelope".format(blendshape_node), 1)

    # Get all blendshape targets and designated target number, as well as active blendshape targets
    highest_target_number = 0 # Our new combination blendshape target's number will be highest + 1
    total_targets = cmds.aliasAttr(blendshape_node, query=True)
    active_targets = []
    targets_dict = {}
    for num in range(0, len(total_targets), 2):
        target_name = total_targets[num]
        targets_dict[target_name] = int(total_targets[num+1].replace("weight[","").replace("]",""))
        if targets_dict[target_name] > highest_target_number:
            highest_target_number = targets_dict[target_name]
        if cmds.getAttr("{}.{}".format(blendshape_node, target_name)) > 0.001:
            active_targets.append(target_name)
    highest_target_number += 1

    # Subtract existing blendshape targets from combination blendshape
    for each in active_targets:
        target_grp_number = targets_dict[each] # blendshape target's designated number in the blendshape node
        target_weight = cmds.getAttr("{}.{}".format(blendshape_node, each)) # If the weights != 1.0, subtracted offsets will need to be modfied at the end
        altered_vertices = cmds.getAttr("{}.inputTarget[0].inputTargetGroup[{}].\
                                        inputTargetItem[6000].inputComponentsTarget".format(blendshape_node, target_grp_number))
        vertex_offsets = cmds.getAttr("{}.inputTarget[0].inputTargetGroup[{}].\
                                        inputTargetItem[6000].inputPointsTarget".format(blendshape_node, target_grp_number))
        # Get all the vertices in the existing target mesh that 
        # need to be subtracted from the combination blendshape
        alt_verts_flattened = []
        for vert_grp in altered_vertices: # altered_vertices list is condensed, and needs to be uncondensed to 
                                          # match the length and direct relationship of the items in the vertex_offsets list
            vert_grp_flattened = cmds.ls("{}.{}".format(inverted_shape, vert_grp), flatten=True)
            alt_verts_flattened.extend(vert_grp_flattened)
        # Clean up any offset values that are so small 
        # that they are actually supposed to be 0
        offsets_corrected = []
        altered_verts_clean = []
        pos_num = 0
        for offset in vertex_offsets:
            offset=list(offset)
            num = 0
            for val in offset[0:3]:
                if val < 0.0001 and val > -0.0001:
                    offset[num] = 0.0
                num += 1
            if offset == [0.0, 0.0, 0.0, 1.0]:
                pos_num += 1
                continue
            else:
                offsets_corrected.append(offset)
                altered_verts_clean.append(alt_verts_flattened[pos_num])
                pos_num += 1

        # Subtract the offsets of the active blendshape from the 
        # inverted combination blendshape (var: inverted_shape)
        for vertex in altered_verts_clean:
            num = altered_verts_clean.index(vertex)
            if vertex_offsets[num] == (0.0, 0.0, 0.0, 1.0):
                continue
            else:
                cmds.xform(vertex, 
                           translation=[-offsets_corrected[num][0] * target_weight, 
                                        -offsets_corrected[num][1] * target_weight, 
                                        -offsets_corrected[num][2] * target_weight], 
                           relative=True)
    
    # Combination Blendshape Command Connects active targets to combination blendshape
    combination_shape_command  = "combinationShape -blendShape \"{}\"".format(blendshape_node) 
    combination_shape_command += "-combinationTargetIndex {}".format(int(highest_target_number))
    for each in active_targets:
        combination_shape_command += "-driverTargetIndex {}".format(targets_dict[each])
    combination_shape_command += "-combineMethod 0;"

    # Finalize Combination blendshape and delete leftover data
    cmds.blendShape(blendshape_node, 
                    edit   = True, 
                    target = [src_mesh, highest_target_number, inverted_shape, 1], 
                    weight = [highest_target_number, 0])
    mel.eval(combination_shape_command)
    cmds.delete(inverted_shape)