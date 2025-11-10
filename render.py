import bpy, math, mathutils, os, sys, glob

MODEL_DIR = os.environ.get("MODEL_DIR", ".")
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "./render/")
IMG = 70
TILT = float(os.environ.get("TILT", "60"))              # 90 = top-down
ENGINE = os.environ.get("ENGINE", "CYCLES")             # CYCLES is robust headless
UNLIT = os.environ.get("UNLIT", "1") == "1"             # emission-only

# Find all GLB/GLTF files in the directory
glb_files = glob.glob(os.path.join(MODEL_DIR, "*.glb")) + glob.glob(os.path.join(MODEL_DIR, "*.gltf"))
if not glb_files:
    raise Exception(f"No GLB/GLTF files found in {MODEL_DIR}")

print(f"Found {len(glb_files)} model(s) to render: {[os.path.basename(f) for f in glb_files]}")

# Process each model
for model_idx, MODEL_PATH in enumerate(glb_files):
    model_name = os.path.splitext(os.path.basename(MODEL_PATH))[0]
    print(f"\n{'='*60}")
    print(f"Processing model {model_idx + 1}/{len(glb_files)}: {model_name}")
    print(f"{'='*60}")

    # --- clean scene
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    # --- import
    ext = os.path.splitext(MODEL_PATH)[1].lower()
    if ext == ".obj":
        bpy.ops.import_scene.obj(filepath=MODEL_PATH)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=MODEL_PATH)
    elif ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=MODEL_PATH)
    else:
        raise Exception(f"Unsupported model type: {ext}")

    # collect all mesh objs
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not meshes:
        print(f"⚠️  No mesh objects after import for {model_name}, skipping.")
        continue

    # ensure render visibility
    for o in meshes:
        o.hide_set(False); o.hide_viewport = False; o.hide_render = False

    # compute combined world-space AABB
    mins = mathutils.Vector((1e9,1e9,1e9))
    maxs = mathutils.Vector((-1e9,-1e9,-1e9))
    for o in meshes:
        for corner in o.bound_box:
            wc = o.matrix_world @ mathutils.Vector(corner)
            mins.x, mins.y, mins.z = min(mins.x, wc.x), min(mins.y, wc.y), min(mins.z, wc.z)
            maxs.x, maxs.y, maxs.z = max(maxs.x, wc.x), max(maxs.y, wc.y), max(maxs.z, wc.z)

    center = (mins + maxs) * 0.5
    size = max((maxs - mins).length, 1e-6)

    # move ALL imported objects so center is at origin
    for o in meshes:
        o.location -= center

    # recompute dims at origin
    mins2 = mathutils.Vector((1e9,1e9,1e9))
    maxs2 = mathutils.Vector((-1e9,-1e9,-1e9))
    for o in meshes:
        for corner in o.bound_box:
            wc = o.matrix_world @ mathutils.Vector(corner)
            mins2.x, mins2.y, mins2.z = min(mins2.x, wc.x), min(mins2.y, wc.y), min(mins2.z, wc.z)
            maxs2.x, maxs2.y, maxs2.z = max(maxs2.x, wc.x), max(maxs2.y, wc.y), max(maxs2.z, wc.z)

    dims = maxs2 - mins2
    footprint = max(dims.x, dims.y)  # X-Y for ortho scale (Blender Z up)

    # === UNLIT with vertex color OR texture ===
    if UNLIT:
        for o in meshes:
            if o.type != "MESH":
                continue
            mat = bpy.data.materials.new(name=f"Unlit_{o.name}")
            mat.use_nodes = True
            nt = mat.node_tree
            for n in list(nt.nodes):
                nt.nodes.remove(n)
            out = nt.nodes.new("ShaderNodeOutputMaterial")
            emi = nt.nodes.new("ShaderNodeEmission")
            nt.links.new(emi.outputs["Emission"], out.inputs["Surface"])

            color_linked = False

            # Try vertex color first
            attr = nt.nodes.new("ShaderNodeAttribute")
            for name in ["Col", "COLOR", "COLOR_0", "color"]:
                if o.data.color_attributes.get(name):
                    attr.attribute_name = name
                    nt.links.new(attr.outputs["Color"], emi.inputs["Color"])
                    color_linked = True
                    break

            # If no vertex color, try texture from Principled
            if not color_linked and o.data.materials:
                src_mat = o.data.materials[0]
                if src_mat.use_nodes:
                    for node in src_mat.node_tree.nodes:
                        if node.type == 'TEX_IMAGE':
                            tex = nt.nodes.new("ShaderNodeTexImage")
                            tex.image = node.image
                            nt.links.new(tex.outputs["Color"], emi.inputs["Color"])
                            color_linked = True
                            break

            # If still nothing, default to neutral gray
            if not color_linked:
                emi.inputs["Color"].default_value = (0.8, 0.8, 0.8, 1.0)

            o.data.materials.clear()
            o.data.materials.append(mat)


    # renderer
    scene = bpy.context.scene
    scene.render.engine = ENGINE
    scene.render.resolution_x = IMG
    scene.render.resolution_y = IMG
    scene.render.film_transparent = True
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'

    if ENGINE == "CYCLES":
        scene.cycles.samples = 32
        scene.cycles.device = 'CPU'

    # camera + target
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0,0,0))
    target = bpy.context.object

    bpy.ops.object.camera_add()
    cam = bpy.context.object
    scene.camera = cam
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = max(footprint * 1.2, 0.01)
    cam.data.clip_start = 0.001
    cam.data.clip_end = 10000.0

    # TRACK-TO so it ALWAYS looks at the model
    trk = cam.constraints.new(type='TRACK_TO')
    trk.target = target
    trk.track_axis = 'TRACK_NEGATIVE_Z'
    trk.up_axis = 'UP_Y'

    # place camera on a tilted ring outside the bbox
    radius = max(dims.length * 1.5, 1.0)
    tilt = math.radians(TILT)
    cam.location = (radius * math.sin(tilt), -radius * math.cos(tilt), radius * math.cos(tilt))

    # Sun light if not unlit
    if not UNLIT:
        bpy.ops.object.light_add(type='SUN', location=(3, -3, 5))
        bpy.context.object.data.energy = 2.0


    # --- render 60 angles ---
    for i in range(60):
        angle = math.pi + (i / 60) * 2 * math.pi
        cam.location = (radius * math.sin(angle) * math.sin(tilt),
                        -radius * math.cos(angle) * math.sin(tilt),
                        radius * math.cos(tilt))
        scene.render.filepath = os.path.join(os.path.dirname(OUTPUT_PATH), f"{model_name}_{i:03d}.png")
        bpy.ops.render.render(write_still=True)
    print(f"✅ Rendered 60 angles for {model_name}.")

print(f"\n{'='*60}")
print(f"✅ All {len(glb_files)} model(s) rendered successfully!")
print(f"{'='*60}")

