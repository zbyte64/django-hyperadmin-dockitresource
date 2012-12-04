from hyperadmin.resources.crud.endpoints import ListEndpoint, CreateEndpoint as BaseCreateEndpoint, DetailEndpoint, DeleteEndpoint, CreateLinkPrototype as BaseCreateLinkPrototype, UpdateLinkPrototype, DeleteLinkPrototype

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
    def get_links(self):
        return {'create':CreateLinkPrototype(endpoint=self)}

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

class DotpathListEndpoint(ListEndpoint):
    pass

class DotpathCreateEndpoint(CreateEndpoint):
    url_suffix = r'^(?P<dotpath>[\w\.]+)/add/$'
    
    def get_links(self):
        return {'create':DotpathCreateLinkPrototype(endpoint=self)}
    
    def get_url(self):
        return super(CreateEndpoint, self).get_url(pk=self.state.parent.instance.pk, dotpath=self.state.dotpath)

class DotpathDetailEndpoint(DetailEndpoint):
    url_suffix = r'^(?P<dotpath>[\w\.]+)/$'
    
    def get_links(self):
        return {'update':DotpathUpdateLinkPrototype(endpoint=self),
                'rest-update':DotpathUpdateLinkPrototype(endpoint=self, link_kwargs={'method':'PUT'}),
                'rest-delete':DotpathDeleteLinkPrototype(endpoint=self, link_kwargs={'method':'DELETE'}),}
    
    def get_url(self, item):
        return super(DetailEndpoint, self).get_url(pk=item.instance.pk, dotpath=item.dotpath or self.state.dotpath)

class DotpathDeleteEndpoint(DeleteEndpoint):
    url_suffix = r'^(?P<dotpath>[\w\.]+)/delete/$'
    
    def get_links(self):
        return {'delete':DotpathDeleteLinkPrototype(endpoint=self)}
    
    def get_url(self, item):
        return super(DeleteEndpoint, self).get_url(pk=item.instance.pk, dotpath=item.dotpath or self.state.dotpath)

