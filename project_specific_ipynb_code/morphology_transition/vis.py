import Interface as I
from .df_from_cell import get_section_description_with_parent

def visualize_matches(start_cell, target_cell, matches):
    fig = I.plt.figure(figsize = (30,30), dpi = 200)
    ax1 = fig.add_subplot(111)
    df = get_section_description_with_parent(start_cell)
    d1 = df.sort_values('soma_distance')
    df = get_section_description_with_parent(target_cell)
    d2 = df.sort_values('soma_distance') 
    
    
    x_offset = 500
    for sec in start_cell.sections:
        xs = [pt[0] for pt in sec.pts]
        zs = [pt[2] for pt in sec.pts]
        if not start_cell.sections.index(sec) in d1.index:
            ax1.plot(xs,zs, color = 'k', linewidth = 0.5)
        else:
            ax1.plot(xs,zs, color = 'green', linewidth = 0.5)

    ax1.set_aspect('equal')

    for sec in target_cell.sections:
        xs = [pt[0] + x_offset for pt in sec.pts]
        zs = [pt[2] for pt in sec.pts]
        if not target_cell.sections.index(sec) in d2.index:
            ax1.plot(xs,zs, color = 'k', linewidth = 0.5)
        else:
            ax1.plot(xs,zs, color = 'green', linewidth = 0.5)    
    for m in matches:
        if isinstance(m[0], str):
            continue
        if isinstance(m[1], str):
            continue
        pts = start_cell.sections[m[0]].pts
        x,y,z = pts[len(pts)//2]
        pts = target_cell.sections[m[1]].pts
        x2,y2,z2 = pts[len(pts)//2]
        I.plt.plot([x,x2+x_offset], [z,z2])
