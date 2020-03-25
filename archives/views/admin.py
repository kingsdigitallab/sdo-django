# Create your views here.
import datetime

from django.http import HttpResponse
from django.template import RequestContext
from django.shortcuts import render_to_response
from lxml import etree

from archives.models import Collection, Container, Document, Repository


############## Reports ####################

def repository(request):
    return render_to_response(
        "admin/report/repository.html",
        {'repository_list': Repository.objects.all()},
        RequestContext(request, {}),
    )


def collection(request):
    return render_to_response(
        "admin/report/collection.html",
        {'collection_list': Collection.objects.all()},
        RequestContext(request, {}),
    )


def container(request, byContentType):

    if byContentType == 'correspondence':
        byContentType = '1'
        elementName = 'Correspondence'

    elif byContentType == 'diary':
        byContentType = '2'
        elementName = 'Diary'

    elif byContentType == 'lessonbook':
        byContentType = '3'
        elementName = 'Lessonbook'
    else:
        byContentType = '4'
        elementName = 'Other'

    return render_to_response(
        "admin/report/container.html",
        {'container_list': Container.objects.filter(content_type=byContentType).order_by('collection'),
         'page_title': elementName,
         },

        RequestContext(request, {}),
    )

############## Exports ####################


def xsd(request, schema_type):

    # map the value passed in the url to the value stored in table (for url
    # readability)
    if schema_type == 'correspondence-metadata':
        schema_type = '1'
        elementName = 'correspondence'

    elif schema_type == 'diary-metadata':
        schema_type = '2'
        elementName = 'diary'

    elif schema_type == 'lessonbook-metadata':
        schema_type = '3'
        elementName = 'lessonbook'
    else:
        schema_type = '4'
        elementName = 'other'

    SDO_NAMESPACE = "http://www.cch.kcl.ac.uk/schenker"
    TEI_NAMESPACE = "http://www.tei-c.org/ns/1.0"
    MODS_NAMESPACE = "http://www.loc.gov/mods/v3"
    XLINK_NAMESPACE = "http://www.w3.org/1999/xlink"
    XS_NAMESPACE = "http://www.w3.org/2001/XMLSchema"
    XS = "{%s}" % XS_NAMESPACE
    DC_NAMESPACE = "http://purl.org/dc/elements/1.1/"
    DCTERMS_NAMESPACE = "http://purl.org/dc/terms/"

    NSMAP = {None: SDO_NAMESPACE,
             'sdo': SDO_NAMESPACE,
             'tei': TEI_NAMESPACE,
             'mods': MODS_NAMESPACE,
             'xlink': XLINK_NAMESPACE,
             'xs': XS_NAMESPACE,
             'dc': DC_NAMESPACE,
             'dcterms': DCTERMS_NAMESPACE
             }

    xml = ""

    schema = etree.Element(XS + "schema", nsmap=NSMAP)
    element = etree.SubElement(schema, XS + "element", nsmap=NSMAP)
    complexType = etree.SubElement(element, XS + "complexType", nsmap=NSMAP)
    attribute = etree.SubElement(complexType, XS + "attribute", nsmap=NSMAP)
    simpleType = etree.SubElement(attribute, XS + "simpleType", nsmap=NSMAP)
    restriction = etree.SubElement(simpleType, XS + "restriction", nsmap=NSMAP)

    schema.append(etree.Comment("Generated: " + str(datetime.date.today())))
    element.set('name', elementName)
    attribute.set('use', 'required')
    attribute.set('name', 'shelfmark')
    restriction.set('base', 'xs:string')

    for document in Document.objects.filter(
            container__content_type=schema_type):
        con = document.container
        coll = con.collection
        rep = coll.repository

        shelfmark = ""
        description = ""

        # If there is not a collection identifier, look for a
        # repository identifier, and use it as the first piece of
        # shelfmark info.
        if rep.identifier:
            shelfmark += rep.identifier + "-"

        if coll.identifier:
            shelfmark += coll.identifier + "-"
            description += "Collection: " + coll.name

        # series
        if con.series:
            description += " Series: " + con.series
        # box
        if con.box:
            shelfmark += con.box + "-"
            description += " Box: " + con.box

        # folder
        if con.folder:
            shelfmark += con.folder + "_"
            description += " Folder/File: " + con.folder

        # unitid
        shelfmark += document.unitid
        description += " Id: " + document.unitid + \
            " (Repository: " + rep.name + ")"

        if document.description:
            description += "Description: " + document.description

        enumeration = etree.SubElement(
            restriction, XS + "enumeration", nsmap=NSMAP)
        enumeration.set('value', shelfmark)

        annotation = etree.SubElement(
            enumeration, XS + "annotation", nsmap=NSMAP)
        documentation = etree.SubElement(
            annotation, XS + "documentation", nsmap=NSMAP)
        documentation.text = description
    xml += etree.tostring(schema, encoding='utf-8', pretty_print=True)
    return HttpResponse(xml, content_type='text/xml')
