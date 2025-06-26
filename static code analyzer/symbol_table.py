# import clang.cindex as clang

class Symbol:
    def __init__(self, name, decl_node, type_str=None):
        self.name = name
        self.decl_node = decl_node
        self.type = type_str  # NEW: store type string here
        self.use_count = 0
        self.is_initialized = False

class Scope:
    def __init__(self, parent=None):
        self.parent = parent
        self.symbols = {}  

    def declare(self, name, node, type_str=None):
        if name not in self.symbols:
            self.symbols[name] = Symbol(name, node, type_str)

    def use(self, name):
        sym = self.lookup(name)
        if sym:
            sym.use_count += 1

    def initialize(self, name):
        sym = self.lookup(name)
        if sym:
            sym.is_initialized = True
            

    def lookup(self, name):
        if name in self.symbols:
            return self.symbols[name]
        elif self.parent:
            return self.parent.lookup(name)
        else:
            return None