from hyperadmin.resources.crud.changelist import ChangeList, FilterSection

class DocumentChangeList(ChangeList):
    def __init__(self, resource):
        super(DocumentChangeList, self).__init__(resource)
        self.detect_sections()
    
    @property
    def document(self):
        return self.resource.model
    
    def detect_sections(self):
        return
    
    def get_paginator_kwargs(self):
        return {'per_page':self.resource.list_per_page,}
    
    def get_links(self, state):
        links = super(DocumentChangeList, self).get_links(state)
        #links += self.getchangelist_sort_links(state)
        return links
    
    def get_changelist_sort_links(self, state):
        links = list()
        return links

class DotpathChangeList(ChangeList):
    def __init__(self, resource):
        super(DotpathChangeList, self).__init__(resource)
        self.detect_sections()
    
    @property
    def document(self):
        return self.resource.model
    
    def populate_state(self, state):
        pass
    
    def detect_sections(self):
        return
    
    def get_paginator_kwargs(self):
        return {}
    
    def get_links(self, state):
        return []
