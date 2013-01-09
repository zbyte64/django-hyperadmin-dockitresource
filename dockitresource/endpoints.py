from hyperadmin.resources.crud.endpoints import ListEndpoint, CreateEndpoint as BaseCreateEndpoint, DetailEndpoint, DeleteEndpoint, CreateLinkPrototype as BaseCreateLinkPrototype, UpdateLinkPrototype, DeleteLinkPrototype, IndexMixin

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

class DotpathMixin(IndexMixin):
    state_class = DotpathEndpointState
    parent_index_name = 'primary'
    parent_url_param_map = {}
    url_param_map = {}
    
    def get_parent_index(self):
        if not self.api_request:
            return self.resource.parent.get_index(self.parent_index_name)
        if 'parent_index' not in self.state:
            self.state['parent_index'] = self.resource.parent.get_index(self.parent_index_name)
            self.state['parent_index'].populate_state()
        return self.state['parent_index']
    
    def get_url_param_map(self):
        return dict(self.url_param_map)
    
    def get_parent_url_param_map(self):
        return dict(self.parent_url_param_map)
    
    def get_url_suffix_parts(self):
        param_map = self.get_parent_url_param_map()
        parts = self.get_parent_index().get_url_params(param_map)
        parts.append(self.resource.rel_name)
        param_map = self.get_url_param_map()
        parts.extend(self.get_index().get_url_params(param_map))
        return parts
    
    def get_url_suffix(self):
        #CONSIDER: the parent endpoint is both a resource and a detail endpoint of another resource
        #if we roll the url then we should lookup the details from the parent endpoint/resource
        parts = self.get_url_suffix_parts()
        url_suffix = '/'.join(parts)
        url_suffix = '^%s%s' % (url_suffix, self.url_suffix)
        return url_suffix
    
    def get_parent_instance(self):
        if 'parent' in self.common_state:
            return self.common_state['parent'].instance
        #todo pick kwargs based on index params
        return self.get_parent_index().get(pk=self.kwargs['pk'])
    
    def get_parent_item(self):
        return self.resource.parent.get_resource_item(self.get_parent_instance())
    
    def get_url_params_from_parent(self, item):
        param_map = self.get_parent_url_param_map()
        return self.get_parent_index().get_url_params_from_item(item, param_map)
    
    def get_url_params_from_item(self, item):
        param_map = self.get_url_param_map()
        return self.get_index().get_url_params_from_item(item, param_map)
    
    def get_url(self, item=None):
        if item is None:
            item = self.state.item
        parent_item = self.get_parent_item()
        params = self.get_url_params_from_parent(parent_item)
        params.update(self.get_url_params_from_item(item))
        return self.reverse(self.get_url_name(), **params)
    
    def get_resource_subitem(self, instance, **kwargs):
        kwargs.setdefault('endpoint', self)
        return self.resource.get_resource_subitem(instance, **kwargs)
    
    @property
    def is_sublisting(self):
        return self.state.is_sublisting
    
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

class DotpathListEndpoint(DotpathMixin, ListEndpoint):
    prototype_method_map = {
        'GET': 'update',
        'POST': 'update',
        'PUT': 'rest-update',
        'DELETE': 'rest-delete',
    }
    
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
    create_prototype = DotpathCreateLinkPrototype
    url_suffix = r'/add/$'

class DotpathDetailEndpoint(DotpathMixin, DetailEndpoint):
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
    delete_prototype = DotpathDeleteLinkPrototype
