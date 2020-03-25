from archives.models import Document
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, render_to_response
from django.template import Context, loader


def index(request):
    return HttpResponseRedirect('admin')


def dates(request):
    docs = Document.objects.all()
    template = loader.get_template('dates.xml')
    context = Context({'docs': docs})
    return HttpResponse(template.render(context), content_type='text/xml')


def document(request, id):
    doc = get_object_or_404(Document, pk=id)
    return render_to_response(
        'document.xml', {'doc': doc}, content_type='text/xml')
