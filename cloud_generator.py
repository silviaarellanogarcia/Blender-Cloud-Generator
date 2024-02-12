import bpy
import random
import bmesh
import numpy as np
import math

### CLOUD GENERATOR ###

def set_up_world_sun_light(sun_config=None, strength=1.0):
    world_node_tree = bpy.context.scene.world.node_tree
    world_node_tree.nodes.clear()

    node_location_x_step = 300
    node_location_x = 0

    node_sky = world_node_tree.nodes.new(type="ShaderNodeTexSky")
    # Set the altitude of the cloud, so we see an accurate blue as background.
    node_sky.altitude = 5000
    # This helps in having a clean "Shading board"
    node_location_x += node_location_x_step

    world_background_node = world_node_tree.nodes.new(type="ShaderNodeBackground")
    world_background_node.inputs["Strength"].default_value = strength
    world_background_node.location.x = node_location_x
    node_location_x += node_location_x_step

    world_output_node = world_node_tree.nodes.new(type="ShaderNodeOutputWorld")
    world_output_node.location.x = node_location_x

    world_node_tree.links.new(node_sky.outputs["Color"], world_background_node.inputs["Color"])
    world_node_tree.links.new(world_background_node.outputs["Background"], world_output_node.inputs["Surface"])

def set_up_material_cloud(density=0.3, color=1.0, random_color=False):
    my_material = bpy.data.materials.new(name="Material_Cloud")
    my_material.use_nodes = True
    bpy.context.object.active_material = my_material
    mat_nodes = my_material.node_tree.nodes
    mat_nodes.clear()
    
    node_location_x_step = 300
    node_location_x = 0
    
    volume_principled_node = mat_nodes.new(type="ShaderNodeVolumePrincipled")
    if random_color:
        color = random.uniform(0.2, 1)
    
    # Specify the color an the density of the cloud
    volume_principled_node.inputs["Color"].default_value = (color, color, color, 1)
    volume_principled_node.inputs["Density"].default_value = density
    
    # This helps in having a clean "Shading board"
    volume_principled_node.location.x = node_location_x
    node_location_x += node_location_x_step
    
    mat_output_node = mat_nodes.new(type="ShaderNodeOutputMaterial")
    mat_output_node.location.x = node_location_x
    
    my_material.node_tree.links.new(mat_output_node.inputs["Volume"], volume_principled_node.outputs["Volume"])
    
    

def main():
    # Delete the objects in the scene and start with a clean scenario
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.select_by_type(type='MESH')
    bpy.ops.object.delete()

    # Creation of an ico-sphere, which will be our firs approach to the cloud mesh
    bpy.ops.mesh.primitive_ico_sphere_add(enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))


    # Linear transformation --> Scaling
    # This will give the icosphere the shape of an "average" cloud
    bpy.context.active_object.scale[0] = random.uniform(1, 4)
    bpy.context.active_object.scale[1] = random.uniform(5, 8)
    bpy.context.active_object.scale[2] = random.uniform(1, 4)

    # Get the active mesh
    context = bpy.context
    ob = context.object
    me = ob.data
    # New bmesh --> Structure for representing and manipulating a mesh structure.
    bm = bmesh.new()

    # subdivide, so we have more vertices in each face and we can apply transformations more precisely
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.subdivide(number_cuts=2)

    # Selection of some vertices of the positive Z axis
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.mesh.select_mode(type='VERT')

    # We need to be in object mode to select specific vertices
    bpy.ops.object.mode_set(mode = 'OBJECT')
    
    # For the cloud to look more natural and random, we translate some vertices.
    # The code offers two options, translating three vertices or only translating one.
    '''
    # Select 3 random vertices and transform the position of some vertices around it.
    selected_indices = random.sample(range(1, len(me.vertices) - 1), 3)

    for i in selected_indices:
        ob.data.vertices[i].select = True
        bpy.ops.object.mode_set(mode = 'EDIT')
        selected_vertex = bpy.context.active_object.data.vertices[i]
        z_coordinate = selected_vertex.co.z
        # Translation of all the points in a certain radius of the selected point, varying only the Z coordinate.
        applied_translation = (0, 0, 1 * np.sign(z_coordinate))
        bpy.ops.transform.translate(value=applied_translation,
                                mirror=True, 
                                use_proportional_edit=True, 
                                proportional_edit_falloff='SMOOTH',
                                proportional_size=3)
                                
    '''

    # Same procedure, only with the vertex of the most negative Z (center)
    ob.data.vertices[0].select = True
    bpy.ops.object.mode_set(mode = 'EDIT')
    selected_vertex = bpy.context.active_object.data.vertices[0]
    z_coordinate = selected_vertex.co.z
    applied_translation = (0, 0, 2 * np.sign(z_coordinate))
    bpy.ops.transform.translate(value=applied_translation,
                            mirror=True, 
                            use_proportional_edit=True, 
                            proportional_edit_falloff='SMOOTH', # TRY WITH RANDOM
                            proportional_size=3)

    # Add a subdivision modifier to smooth the surface (interpolation)
    bpy.ops.object.modifier_add(type='SUBSURF')
    bpy.context.object.modifiers["Subdivision"].levels = 3
    bpy.context.object.modifiers["Subdivision"].render_levels = 2


    # Add a displace modifier --> displace the vertices of the mesh along their normals according to the values of the texture
    # In this case, it makes the cloud fluffier.
    bpy.ops.object.modifier_add(type='DISPLACE')

    # Create a new texture for the displace modifier
    texture = bpy.data.textures.new("Texture", type='CLOUDS')
    # We don't want the cloud to be very deformed, so we look at the noise image closer 
    texture.noise_scale = random.uniform(0.6, 1.3)
    texture.noise_depth = 1
    texture.noise_basis = 'ORIGINAL_PERLIN'

    # Assign the texture to the displace modifier.
    displace_modifier = bpy.context.object.modifiers["Displace"]
    displace_modifier.texture = texture

    bpy.ops.object.mode_set(mode='OBJECT')


    # Set shading type in the 3D Viewport space
    view_3d_area = next((area for area in bpy.context.screen.areas if area.type == 'VIEW_3D'), None)
    view_3d_area.spaces.active.shading.type = 'MATERIAL'

    bpy.context.scene.render.engine = 'CYCLES'

    bpy.context.scene.world.node_tree
    
    # Modify the background, and consequently the lighting 
    sun_config = {"sun_rotation": math.radians(random.randint(0, 360))}
    set_up_world_sun_light(sun_config=sun_config, strength=0.2)
    
    # Add and custom a material for the cloud
    set_up_material_cloud(density=0.8, random_color=True)
    
    # Rotate the cloud, so the "bump" is oriented upwards
    bpy.ops.transform.rotate(value=math.radians(180), orient_axis='Y', 
                            orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)), 
                            constraint_axis=(False, True, False), 
                            use_proportional_edit=False)

if __name__ == "__main__":
    main()
