new_emotion_code = """        # Emotion Visualization
        emotion_code = ""
        if spec.emotion_config:
            ec = spec.emotion_config
            mood = ec.get("mood", "neutral")
            valence = ec.get("valence", 0.0)
            arousal = ec.get("arousal", 0.5)
            intensity = max(0.1, min(1.0, abs(valence) * 0.5 + arousal * 0.5))

            if valence < -0.3:
                base_color = (0.2, 0.3, 1.0, 1.0)
            elif valence > 0.3:
                base_color = (1.0, 0.6, 0.1, 1.0)
            else:
                base_color = (0.8, 0.8, 0.9, 1.0)

            emotion_code = f"""
# Emotion Visualization
# Mood: {mood}, Valence: {valence:.2f}, Arousal: {arousal:.2f}

# Create emotion sphere at center
bpy.ops.mesh.primitive_uv_sphere_add(location=(0, 0, 3), radius={max(0.1, min(1.0, abs(valence) * 0.5 + arousal * 0.5))})
emotion_obj = bpy.context.active_object
emotion_obj.name = "EmotionCore"
emotion_obj.scale = ({max(0.1, min(1.0, abs(valence) * 0.5 + arousal * 0.5))},) * 3

# Emission material for core
emotion_mat = bpy.data.materials.new(name="EmotionMaterial")
emotion_mat.use_nodes = True
nodes = emotion_mat.node_tree.nodes
emission = nodes.new(type='ShaderNodeEmission')
emission.inputs['Color'].default_value = ({base_color[0]}, {base_color[1]}, {base_color[2]}, 1.0)
emission.inputs['Strength'].default_value = {max(0.1, min(1.0, abs(valence) * 0.5 + arousal * 0.5)) * 10.0}
output = nodes.new(type='ShaderNodeOutputMaterial')
emotion_mat.node_tree.links.new(emission.outputs['Emission'], output.inputs['Surface'])
emotion_obj.data.materials.append(emotion_mat)

# Animate pulse based on arousal
emotion_obj.scale = ({max(0.1, min(1.0, abs(valence) * 0.5 + arousal * 0.5))},) * 3
emotion_obj.keyframe_insert(data_path="scale", frame=1)
emotion_obj.scale = ({max(0.1, min(1.0, abs(valence) * 0.5 + arousal * 0.5)) * 1.3},) * 3
emotion_obj.keyframe_insert(data_path="scale", frame=int({int(spec.duration) * int(spec.fps) / 2}))
emotion_obj.scale = ({max(0.1, min(1.0, abs(valence) * 0.5 + arousal * 0.5))},) * 3
emotion_obj.keyframe_insert(data_path="scale", frame=int({int(spec.duration) * int(spec.fps)}))

# Lighting based on valence
bpy.ops.object.light_add(type='SUN', location=(0, 0, 10))
sun = bpy.context.active_object
sun.name = "EmotionSun"
sun.data.energy = max(1.0, {arousal} * 5.0)
if {valence} < -0.3:
    sun.data.color = (0.3, 0.4, 1.0)
elif {valence} > 0.3:
    sun.data.color = (1.0, 0.7, 0.3)
else:
    sun.data.color = (0.9, 0.9, 1.0)

# Background color shift based on mood
world = bpy.context.scene.world
if world is None:
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
world.use_nodes = True
bg_nodes = world.node_tree.nodes
bg_emission = bg_nodes.new(type='ShaderNodeEmission')
if {valence} < -0.3:
    bg_emission.inputs['Color'].default_value = (0.05, 0.1, 0.2, 1.0)
elif {valence} > 0.3:
    bg_emission.inputs['Color'].default_value = (0.2, 0.15, 0.05, 1.0)
else:
    bg_emission.inputs['Color'].default_value = (0.1, 0.1, 0.15, 1.0)
bg_emission.inputs['Strength'].default_value = {arousal * 0.5 + 0.1}
bg_output = bg_nodes.new(type='ShaderNodeOutputWorld')
world.node_tree.links.new(bg_emission.outputs['Emission'], bg_output.inputs['Surface'])
"""
else:
    emotion_code = ""
'''