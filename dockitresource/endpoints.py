from django.views.generic.detail import SingleObjectMixin

from hyperadmin.resources.crud.endpoints import ListEndpoint as BaseListEndpoint, CreateEndpoint as BaseCreateEndpoint, DetailEndpoint as BaseDetailEndpoint, DeleteEndpoint as BaseDeleteEndpoint, CreateLinkPrototype as BaseCreateLinkPrototype, UpdateLinkPrototype, DeleteLinkPrototype

from dockitresource.states import DotpathEndpointState

from dockit.schema.common import UnSet


class DocumentMixin(object):
    document = None
    queryset = None
    
    def get_queryset(self):
        return self.resource.get_queryset(self.api_request.user)
    
    def get_resource_subitem(self, instance, **kwargs):
        kwargs.setdefault('endpoint', self)
        return self.resource.get_resource_subitem(instance, **kwargs)

class DocumentDetailMixin(DocumentMixin, SingleObjectMixin):
    def get_object(self):
        if not hasattr(self, 'object'):
            self.object = SingleObjectMixin.get_object(self)
        return self.object

class DotpathMixin(DocumentDetailMixin):
    state_class = DotpathEndpointState
    
    @property
    def is_sublisting(self):
        return self.state.is_sublisting
    
    def get_parent_item(self):
        if not getattr(self, 'object', None):
            self.object = self.get_object()
        return self.resource.parent.get_resource_item(self.object)
    
    def get_common_state_data(self):
        data = super(DotpathMixin, self).get_common_state_data()
        data['dotpath'] = self.kwargs['dotpath']
        data['parent'] = self.get_parent_item()
        data['item'] = self.get_item()
        return data
    
    def get_item(self):
        if not getattr(self, 'object', None):
            self.object = self.get_object()
        dotpath = self.kwargs['dotpath']
        return self.get_resource_item(self.object, dotpath=dotpath)
    
    #def get_state_data(self):
    #    data = super(DotpathMixin, self).get_state_data()
    #    data['parent'] = self.get_parent_item()
    #    return data
    
    def get_link_kwargs(self, **kwargs):
        kwargs = super(DotpathMixin, self).get_link_kwargs(**kwargs)
        if 'item' not in kwargs:
            kwargs['item'] = self.get_item()
        return kwargs
    
    def get_url(self, item=None):
        if item:
            pk = item.instance.pk
            dotpath = item.dotpath
        else:
            pk = self.common_state.parent.instance.pk
            dotpath = self.common_state.dotpath
        return self.reverse(self.get_url_name(), pk=pk, dotpath=dotpath)

class CreateLinkPrototype(BaseCreateLinkPrototype):
    def get_link_kwargs(self, **kwargs):
        form_kwargs = kwargs.pop('form_kwargs', None)
        if form_kwargs is None:
            form_kwargs = {}
        form_kwargs = self.resource.get_form_kwargs(**form_kwargs)
        form_kwargs.setdefault('initial', {})
        
        method = 'POST'
        if kwargs.get('link_factor', None) in ('LO', 'LT'):
            method = 'GET'
        
            if self.resource.schema_select:
                #TODO this is a hack?
                if kwargs.get('rel', None) != 'breadcrumb':
                    kwargs['link_factor'] = 'LT'
                form_class = self.resource.get_create_select_schema_form_class()
            else:
                form_class = self.resource.get_form_class()
        else:
            form_class = self.resource.get_form_class()
        
        link_kwargs = {'url':self.get_url(),
                       'resource':self,
                       'method':method,
                       'form_kwargs':form_kwargs,
                       'form_class': form_class,
                       'prompt':'create',
                       'rel':'create',}
        link_kwargs.update(kwargs)
        return super(CreateLinkPrototype, self).get_link_kwargs(**link_kwargs)

class CreateEndpoint(DocumentMixin, BaseCreateEndpoint):
    create_prototype = CreateLinkPrototype

class ListEndpoint(DocumentMixin, BaseListEndpoint):
    pass

class DetailEndpoint(DocumentDetailMixin, BaseDetailEndpoint):
    pass

class DeleteEndpoint(DocumentDetailMixin, BaseDeleteEndpoint):
    pass

class DotpathCreateLinkPrototype(CreateLinkPrototype):
    def handle_submission(self, link, submit_kwargs):
        form = link.get_form(**submit_kwargs)
        if form.is_valid():
            instance = form.save()
            resource_item = self.resource.get_resource_item(instance, dotpath=form._meta.dotpath)
            return self.on_success(resource_item)
        return link.clone(form=form)

class DotpathUpdateLinkPrototype(UpdateLinkPrototype):
    def handle_submission(self, link, submit_kwargs):
        form = link.get_form(**submit_kwargs)
        if form.is_valid():
            instance = form.save()
            resource_item = self.resource.get_resource_item(instance, dotpath=self.state.dotpath)
            #or send the update link?
            return self.on_success(resource_item)
        return link.clone(form=form)

class DotpathDeleteLinkPrototype(DeleteLinkPrototype):
    def handle_submission(self, link, submit_kwargs):
        instance = self.state.parent.instance
        instance.dot_notation_set_value(self.state.dotpath, UnSet)
        instance.save()
        return self.on_success()


class DotpathListEndpoint(DotpathMixin, ListEndpoint):
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


class DotpathCreateEndpoint(DotpathMixin, CreateEndpoint):
    url_suffix = r'^(?P<dotpath>[\w\.]+)/add/$'
    
    create_prototype = DotpathCreateLinkPrototype

class DotpathDetailEndpoint(DotpathMixin, DetailEndpoint):
    url_suffix = r'^(?P<dotpath>[\w\.]+)/$'
    
    update_prototype = DotpathUpdateLinkPrototype
    delete_prototype = DotpathDeleteLinkPrototype
    
    list_endpoint = DotpathListEndpoint
    
    def handle_link_submission(self, api_request):
        if self.is_sublisting:
            return self.dispatch_list(api_request)
        return super(DotpathDetailEndpoint, self).handle_link_submission(api_request)
    
    def dispatch_list(self, api_request):
        endpoint = self.list_endpoint(parent=self.parent, api_request=self.api_request, name_suffix=self.name_suffix)
        return endpoint.dispatch_api(api_request)

class DotpathDeleteEndpoint(DotpathMixin, DeleteEndpoint):
    url_suffix = r'^(?P<dotpath>[\w\.]+)/delete/$'
    
    delete_prototype = DotpathDeleteLinkPrototype
