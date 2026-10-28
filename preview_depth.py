"""Depth preview shares export's full-resolution visibility and hole-filling rules."""

def views(image, depth, strength=.04, convergence=.5, progress=lambda message:None):
    from depth_views import views as export_views
    return export_views(image,depth,strength,convergence,progress)
