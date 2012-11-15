from hyperadmin.resources.endpoints import EndpointLink, Endpoint
from hyperadmin.resources.crud.endpoints import ListEndpoint, CreateEndpoint, DetailEndpoint, DeleteEndpoint, CreateEndpointLink, UpdateEndpointLink, DeleteEndpointLink

from dockit.schema.common import UnSet

class DotpathCreateEndpointLink(CreateEndpointLink):
    def handle_submission(self, link, submit_kwargs):
        form = link.get_form(**submit_kwargs)
        if form.is_valid():
            instance = form.save()
            resource_item = self.resource.get_resource_item(instance, dotpath=form._meta.dotpath)
            return self.on_success(resource_item)
        return link.clone(form=form)

class DotpathUpdateEndpointLink(UpdateEndpointLink):
    def handle_submission(self, link, submit_kwargs):
        form = link.get_form(**submit_kwargs)
        if form.is_valid():
            instance = form.save()
            resource_item = self.resource.get_resource_item(instance, dotpath=self.state.dotpath)
            #or send the update link?
            return self.on_success(resource_item)
        return link.clone(form=form)

class DotpathDeleteEndpointLink(DeleteEndpointLink):
    def handle_submission(self, link, submit_kwargs):
        instance = self.state.parent.instance
        instance.dot_notation_set_value(self.state.dotpath, UnSet)
        instance.save()
        return self.on_success()

class DotpathCreateEndpoint(DetailEndpoint):
    url_suffix = r'^(?P<dotpath>[\w\.]+)/add/$'
    
    def get_links(self):
        return {'create':DotpathCreateEndpointLink(endpoint=self)}
    
    def get_url(self):
        return super(CreateEndpoint, self).get_url(pk=self.state.parent.instance.pk, dotpath=self.state.dotpath)

class DotpathDetailEndpoint(DetailEndpoint):
    url_suffix = r'^(?P<dotpath>[\w\.]+)/$'
    
    def get_links(self):
        return {'update':DotpathUpdateEndpointLink(endpoint=self),
                'rest-update':DotpathUpdateEndpointLink(endpoint=self, link_kwargs={'method':'PUT'}),
                'rest-delete':DotpathDeleteEndpointLink(endpoint=self, link_kwargs={'method':'DELETE'}),}
    
    def get_url(self, item):
        return super(DetailEndpoint, self).get_url(pk=item.instance.pk, dotpath=item.dotpath or self.state.dotpath)

class DotpathDeleteEndpoint(DeleteEndpoint):
    url_suffix = r'^(?P<dotpath>[\w\.]+)/delete/$'
    
    def get_links(self):
        return {'delete':DotpathDeleteEndpointLink(endpoint=self)}
    
    def get_url(self, item):
        return super(DeleteEndpoint, self).get_url(pk=item.instance.pk, dotpath=item.dotpath or self.state.dotpath)

