from hyperadmin.resources.crud.endpoints import ListEndpoint, CreateEndpoint as BaseCreateEndpoint, DetailEndpoint, DeleteEndpoint, CreateLinkPrototype as BaseCreateLinkPrototype, UpdateLinkPrototype, DeleteLinkPrototype

from dockitresource.states import DotpathEndpointState

from dockit.schema.common import UnSet


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

class CreateEndpoint(BaseCreateEndpoint):
    create_prototype = CreateLinkPrototype

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

class DotpathMixin(object):
    state_class = DotpathEndpointState
    parent_index_name = 'primary'
    
    def get_resource_subitem(self, instance, **kwargs):
        kwargs.setdefault('endpoint', self)
        return self.resource.get_resource_subitem(instance, **kwargs)
    
    def get_parent_index(self):
        if 'parent_index' not in self.state:
            self.state['parent_index'] = self.resource.parent.get_index(self.parent_index_name)
            self.state['parent_index'].populate_state()
        return self.state['parent_index']
    
    def get_parent_instance(self):
        if not hasattr(self, '_parent_instance'):
            #todo pick kwargs based on index params
            self._parent_instance = self.get_parent_index().get(pk=self.kwargs['pk'])
        return self._parent_instance
    
    @property
    def is_sublisting(self):
        return self.state.is_sublisting
    
    def get_parent_item(self):
        return self.resource.parent.get_resource_item(self.get_parent_instance())
    
    def get_common_state_data(self):
        data = super(DotpathMixin, self).get_common_state_data()
        data['dotpath'] = self.kwargs['dotpath']
        data['parent'] = self.get_parent_item()
        data['item'] = self.get_item()
        return data
    
    def get_item(self):
        dotpath = self.kwargs['dotpath']
        return self.get_resource_item(self.get_parent_instance(), dotpath=dotpath)
    
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
