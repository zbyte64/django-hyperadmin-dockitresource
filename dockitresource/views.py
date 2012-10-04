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


#dotpath views:

class DotpathMixin(DocumentDetailMixin):
    @property
    def is_sublisting(self):
        return self.state.is_sublisting
    
    def get_parent_item(self):
        if not getattr(self, 'object', None):
            self.object = self.get_object()
        return self.resource.parent.get_resource_item(self.object)
    
    def get_item(self):
        if not getattr(self, 'object', None):
            self.object = self.get_object()
        if hasattr(self, 'state'):
            dotpath = self.state.dotpath
        else:
            dotpath = self.kwargs['dotpath']
        return self.resource.get_resource_item(self.object, dotpath=dotpath)
    
    def get_state_data(self):
        data = super(DotpathMixin, self).get_state_data()
        data['parent'] = self.get_parent_item()
        return data
    
    def get_create_link(self, **form_kwargs):
        item = self.get_item()
        form_kwargs.update(self.get_form_kwargs())
        link_kwargs = self.get_link_kwargs()
        link_kwargs.update({'form_class': self.get_form_class(),
                            'form_kwargs': form_kwargs,
                            'item':item,})
        return self.resource.get_create_link(**link_kwargs)

class DotpathCreateView(DotpathMixin, DocumentCreateView):
    pass

class DotpathListView(DotpathMixin, DocumentListView):
    def get(self, request, *args, **kwargs):
        return DocumentListView.get(self, request, *args, **kwargs)
    
    def get_meta(self):
        dotpath = self.state.dotpath
        if self.is_sublisting:
            dotpath += '.0'
        resource_item = self.resource.get_list_resource_item(self.state.parent.instance, dotpath=dotpath)
        form = resource_item.get_form()
        data = dict()
        data['display_fields'] = list()
        for field in form:
            data['display_fields'].append({'prompt':field.label})
        return data

class DotpathDeleteView(DotpathMixin, DocumentDeleteView):
    pass

class DotpathDetailView(DotpathMixin, DocumentDetailView):
    def dispatch(self, request, *args, **kwargs):
        self.request = request
        self.args = args
        self.kwargs = kwargs
        self.fork_state()
        if self.is_sublisting:
            return self.dispatch_list(request, *args, **kwargs)
        return super(DotpathDetailView, self).dispatch(request, *args, **kwargs)
    
    def dispatch_list(self, request, *args, **kwargs):
        init = self.resource.get_view_kwargs()
        view = self.resource.list_view.as_view(**init)
        return view(request, *args, **kwargs)
