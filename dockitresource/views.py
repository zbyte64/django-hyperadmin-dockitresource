from dockit.views.detail import SingleObjectMixin

from hyperadmin.resources.crud.views import CRUDDetailMixin, CRUDCreateView, CRUDListView, CRUDDeleteView, CRUDDetailView

class DocumentMixin(object):
    document = None
    queryset = None
    
    def get_queryset(self):
        return self.resource.get_queryset(self.request.user)

class DocumentCreateView(DocumentMixin, CRUDCreateView):
    pass

class DocumentListView(DocumentMixin, CRUDListView):
    pass

class DocumentDetailMixin(DocumentMixin, CRUDDetailMixin, SingleObjectMixin):
    def get_object(self):
        if not hasattr(self, 'object'):
            self.object = SingleObjectMixin.get_object(self)
        return self.object

class DocumentDeleteView(DocumentDetailMixin, CRUDDeleteView):
    pass

class DocumentDetailView(DocumentDetailMixin, CRUDDetailView):
    pass

