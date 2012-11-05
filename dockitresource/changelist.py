from hyperadmin.resources.crud.changelist import ChangeList, FilterSection

class DocumentChangeList(ChangeList):
    @property
    def document(self):
        return self.resource.model
    
    def get_paginator_kwargs(self):
        return {'per_page':self.resource.list_per_page,}
    
    def get_links(self):
        links = super(DocumentChangeList, self).get_links()
        #links += self.getchangelist_sort_links()
        return links
    
    def get_changelist_sort_links(self):
        links = list()
        return links

class DotpathChangeList(ChangeList):
    @property
    def document(self):
        return self.resource.model
    
    def populate_state(self):
        pass
    
    def get_paginator_kwargs(self):
        return {}
    
    def get_links(self):
        return []
