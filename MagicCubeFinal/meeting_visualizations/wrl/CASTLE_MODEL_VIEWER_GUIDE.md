# Castle Model Viewer meeting guide

All coordinates use millimetres. Open Castle Model Viewer yourself, use File → Open, and choose a `.wrl` in this directory. These are standalone VRML97 models with no external textures.

Use Examine navigation. Drag with the left mouse button to rotate, middle-drag (or Shift+left-drag) to pan, and use the wheel/right-drag to zoom. Use Navigation → Jump To Viewpoint for the built-in Isometric, Source-facing (-z), Side (+x), Top (+y), and Rear (+z) cameras. Source-facing looks along +z; the top camera looks down -y. Space stops automatic rotation. Exact menus may differ by release.

Controls reference: [official Castle Model Viewer manual](https://castle-engine.io/castle-model-viewer).

## Recommended files to open during meeting

1. `onecube_source_view.wrl`: explain the point source, 50 mm face distance, and single 2 mm GAGG cube.
2. `magiccube_full_geometry.wrl`: show 2048 GAGG and 2048 K9 elements in the frozen 16-layer arrangement.
3. `magiccube_cutaway.wrl`: use the highly transparent K9 to reveal all internal GAGG locations.
4. `magiccube_exploded_layers.wrl`: show layer order k=0 through k=15 and alternating checkerboards.
5. `magiccube_source_fov.wrl`: explain the 100 mm FOV outline 50 mm from the detector front.
6. `magiccube_geometry_with_source.wrl`: combine the detector, source, FOV, and distance in the main meeting view.
7. `magiccube_validated_response.wrl`, when present: explain actual completed single-source Singles counts using the accompanying legend.

## Physical geometry versus display transformations

OneCube views, full geometry, cutaway, source/FOV, source grid, and geometry-with-source preserve physical element locations and sizes. Cutaway changes only K9 opacity. Detector-ID and response views are physical-position GAGG subsets with K9 omitted. The single-layer model is a physical-position k=0 subset. Exploded and adjacent-layer models move z layers to display z=8*k mm: x/y, cube size, and layer order remain unchanged. They are explicitly marked NOT PHYSICAL GEOMETRY.

The mother outline is 67.2×67.2×32 mm; occupied element bounds are ±32.5 mm in x/y and ±16 mm in z. Air and cylindricalPET bookkeeping are hidden. Source spheres, lines, axes, labels, and grid markers are presentation aids, not physical source volumes or photon tracks. Colors/transparency do not represent optical properties; K9 is the existing provisional glass proxy.

Use Isometric for the full detector/cutaway, Source-facing for checkerboards, Side for depth and source spacing, and Top for an orthogonal overview. For the OneCube close-up, zoom toward its detector; its cube retains true scale despite the long source distance. Transparent surfaces may sort differently by renderer; use the GAGG-only ID/response view for an unobstructed interior.

The source grid comes from the existing full_source_positions.csv (51×51 inclusive endpoints). Its endpoints are a project convention, not a paper-confirmed result. The central validation source is separate from full-grid source_id=0 at a corner.

## Verification and regeneration

Run `python scripts/validate_wrl_visualizations.py`. The generator can be run with `python scripts/generate_wrl_visualizations.py`; it writes only here. No Gate, Slurm, or GUI invocation is needed. The validator checks generated VRML structure and placement, not a Castle rendering session.
