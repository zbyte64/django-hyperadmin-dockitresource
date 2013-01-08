============
Introduction
============

django-hyperadmin-dockitresource a Hyperadmin resource written for documents in django-dockit

------------
Requirements
------------

* Python 2.6 or later
* Django 1.3 or later
* django-hyperadmin
* django-dockit


============
Installation
============

Put 'dockitresource' into your ``INSTALLED_APPS`` section of your settings file.


Registering documents
---------------------

Registering a document with hyperadmin::

    from dockitresource.resources import DocumentResource
    from dockitresource.tests.books_models import Book

    class BookResource(DocumentResource):
        list_display = ('title', 'authors_list', 'publisher', 'year')
    
    hyperadmin.site.register(Book, BookResource)
