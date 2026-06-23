from django.shortcuts import render
from .models import Seat

def seat_map_view(request):
    # Fetch all seats from DB sorted by row and col
    seats = Seat.objects.all().order_by('row', 'col')

    # Mapping from (row, col) to template variable key in seat_map.html
    seat_mapping = {
        (0, 1): "pc1",
        (1, 1): "pc2",
        (2, 1): "pc3",
        (2, 2): "pc4",
        (2, 3): "pc5",
        (2, 4): "pc6",
        (2, 5): "pc7",
        (2, 6): "pc8",
        (5, 0): "pc15",
        (5, 1): "pc16",
        (5, 2): "pc17",
        (5, 3): "pc18",
        (5, 4): "pc19",
        (5, 5): "pc20",
    }

    pc_states = {}
    for seat in seats:
        key = seat_mapping.get((seat.row, seat.col))
        if key:
            # Convert status to boolean for template check (e.g. {% if pc_states.pc15 %})
            pc_states[key] = (seat.status == 'alive')

    context = {
        'pc_states': pc_states,
    }
    return render(request, 'seat_map.html', context)


import os
import markdown
from pathlib import Path
from django.conf import settings
from django.http import Http404, HttpResponseBadRequest

def reports_list_view(request):
    document_dir = (Path(settings.BASE_DIR) / 'document').resolve()
    reports = []
    if document_dir.exists() and document_dir.is_dir():
        for filename in os.listdir(document_dir):
            if filename.endswith('.md'):
                reports.append(filename)
    
    # Sort descending to show newest first
    reports.sort(reverse=True)
    
    context = {
        'reports': reports,
    }
    return render(request, 'reports_list.html', context)

def report_detail_view(request, filename):
    document_dir = (Path(settings.BASE_DIR) / 'document').resolve()
    filepath = (document_dir / filename).resolve()
    
    # Prevent directory traversal
    if document_dir not in filepath.parents and filepath != document_dir:
        return HttpResponseBadRequest("Invalid request.")
        
    if not filepath.exists() or not filepath.is_file() or not filename.endswith('.md'):
        raise Http404("Report not found.")
        
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except OSError:
        raise Http404("Report could not be read.")
        
    # Convert markdown to HTML (supporting extra syntax like tables/code blocks)
    html_content = markdown.markdown(content, extensions=['extra'])
    
    context = {
        'filename': filename,
        'html_content': html_content,
    }
    return render(request, 'report_detail.html', context)


