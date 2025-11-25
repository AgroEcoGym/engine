
def checkissubclass(class_object, class_name):
    name = class_object.__name__
    if name == class_name:
        return True
    else:
        for base in class_object.__bases__:
            checkissubclass(base, class_name)
        return False