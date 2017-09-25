def remove_element(element):
    '''Remove an element from its container element, keeping its tail.'''
    if element.tail:
	if element.getprevious() is not None:
	    element.getprevious().tail = (
		    element.getprevious().tail or '') + element.tail
	else:
	    element.getparent().text = (
		    element.getparent().text or '') + element.tail
    element.getparent().remove(element)
