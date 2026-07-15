with open(r'C:\Users\subur\Documents\New OpenCode Project\web-crawler-agent\src\crawler_agent\cognitive\blender_sandbox.py', 'r') as f:
    lines = f.readlines()

# Fix lines 741-742 (0-indexed: 740, 741)
lines[740] = '            { "bpy.ops.mesh.primitive_plane_add(location=(0, 0, 0), scale=(50, 50, 1))" if spec.ground else "# No ground" }\n'
lines[741] = '            { "ground = bpy.context.active_object; ground.name = \'Ground\'; bpy.ops.rigidbody.object_add(); ground.rigid_body.type = \'PASSIVE\'; ground.rigid_body.collision_shape = \'BOX\'" if spec.ground else "" }\n'

with open(r'C:\Users\subur\Documents\New OpenCode Project\web-crawler-agent\src\crawler_agent\cognitive\blender_sandbox.py', 'w') as f:
    f.writelines(lines)
print('Fixed')