from symbol_table import Scope
# import sys
# import json
# from pathlib import Path
import clang.cindex as clang

clang.Config.set_library_file(r"C:\Program Files\LLVM\bin\libclang.dll")

class Issue:
    def __init__(self, rule_id, msg, line, col):
        self.rule_id = rule_id
        self.msg = msg
        self.line = line
        self.col = col

    def as_dict(self):
        return {
            "rule": self.rule_id,
            "message": self.msg,
            "line": self.line,
            "column": self.col,
        }

    def __str__(self):
        return f"{self.rule_id} {self.line}:{self.col}  {self.msg}"


class Rule:
    rule_id: str = "BASE"
    description: str = "base class"

    def visit(self, node, scope=None) -> list[Issue]:
        return []


class Analyzer:
    def __init__(self):
        self._rules: list[Rule] = []
        self.issues: list[Issue] = []
        self.scope = None  
        self.function_decls = {}  
        self.function_calls = set()  

    def register(self, rule):
        self._rules.append(rule)

    def analyze(self, tu: clang.TranslationUnit):
        for rule in self._rules:
            if hasattr(rule, "reset"):
                rule.reset()
        self.scope = Scope(parent=None)
        
        def recurse(node):
            enter_new_scope = node.kind in {
                clang.CursorKind.FUNCTION_DECL,
                clang.CursorKind.COMPOUND_STMT,
            }
            if enter_new_scope:
                self.scope = Scope(parent=self.scope)

                # If this is a function, declare parameters in the scope
                if node.kind == clang.CursorKind.FUNCTION_DECL:
                    for param in node.get_arguments():
                        self.scope.declare(param.spelling, param, param.type.spelling)

            self.handle_decls_and_uses(node)

            for rule in self._rules:
                self.issues.extend(rule.visit(node, self.scope))

            for child in node.get_children():
                recurse(child)

            if enter_new_scope:
                # Check unused variables and parameters
                for sym in self.scope.symbols.values():
                    if sym.use_count == 0:
                        loc = sym.decl_node.location
                        # Differentiate between parameters and variables
                        issue_type = "UNUSED_PARAM" if sym.decl_node.kind == clang.CursorKind.PARM_DECL else "UNUSED_VAR"
                        issue_msg = f"{'Parameter' if sym.decl_node.kind == clang.CursorKind.PARM_DECL else 'Variable'} '{sym.name}' declared but never used"
                        self.issues.append(
                            Issue(issue_type, issue_msg, loc.line, loc.column)
                        )
                self.scope = self.scope.parent


        recurse(tu.cursor)
        
        
        for sym in self.scope.symbols.values():
            if sym.use_count == 0:
                loc = sym.decl_node.location
                self.issues.append(
                    Issue("UNUSED_VAR",
                        f"Variable '{sym.name}' declared but never used",
                        loc.line, loc.column)
                )
       
        self.check_unused_functions()

    def handle_decls_and_uses(self, node):
        
        if node.kind == clang.CursorKind.VAR_DECL:
            if self.scope:
                var_type = node.type.spelling  
                self.scope.declare(node.spelling, node, var_type)
                
                for child in node.get_children():
                    if child.kind != clang.CursorKind.TYPE_REF:
                        self.scope.initialize(node.spelling)
                        break

      
        elif node.kind == clang.CursorKind.FUNCTION_DECL:
           
            if node.spelling:
                self.function_decls[node.spelling] = node
            

       
        elif node.kind == clang.CursorKind.DECL_REF_EXPR:
            if self.scope:
                self.scope.use(node.spelling)
        
        elif node.kind == clang.CursorKind.CALL_EXPR:
            referenced = node.referenced
            if referenced and referenced.spelling:
                self.function_calls.add(referenced.spelling)
            else:
                # fallback: search children if referenced is None
                for child in node.get_children():
                    if child.kind == clang.CursorKind.DECL_REF_EXPR and child.spelling:
                        self.function_calls.add(child.spelling)
                        break



    def check_unused_functions(self):
        for func_name, node in self.function_decls.items():
         
            if func_name == "main":
                continue
            if func_name not in self.function_calls:
                loc = node.location
                self.issues.append(
                    Issue("UNUSED_FUNC",
                          f"Function '{func_name}' declared but never called",
                          loc.line, loc.column)
                )


class ConstantCondition(Rule):
    rule_id = "CONSTANT_CONDITION"
    description = "Constant condition in if or loop statement"

    def visit(self, node, scope=None):
        if node.kind not in {clang.CursorKind.IF_STMT, clang.CursorKind.WHILE_STMT}:
            return []

        children = list(node.get_children())
        if not children:
            return []

        condition = children[0]
        loc = node.location

        # Gather all tokens in the condition
        tokens = list(condition.get_tokens())
        if not tokens:
            return []

        token_val = tokens[0].spelling

        # Match known constant values
        if token_val in {"0", "false"}:
            return [Issue(self.rule_id, "Condition always false", loc.line, loc.column)]
        elif token_val in {"1", "true"}:
            return [Issue(self.rule_id, "Condition always true", loc.line, loc.column)]

        return []


class EmptyBody(Rule):
    rule_id = "EMPTY_BODY"
    description = "Empty if/while/for body"

    def visit(self, node, scope=None):
        issues = []
        if node.kind in (
            clang.CursorKind.IF_STMT,
            clang.CursorKind.WHILE_STMT,
            clang.CursorKind.FOR_STMT,
        ):
            children = list(node.get_children())
            for child in children:
                # Check if there's a CompoundStmt with no statements inside
                if child.kind == clang.CursorKind.COMPOUND_STMT:
                    if len(list(child.get_children())) == 0:
                        loc = child.location
                        issues.append(
                            Issue(self.rule_id,
                                  f"Empty body in {node.kind.name.lower()} statement",
                                  loc.line, loc.column)
                        )
                elif child.kind == clang.CursorKind.NULL_STMT:
                    # Semicolon is a null statement; this is NOT an empty body, skip reporting
                    return []
        return issues



BREAK_TERMINATORS = {
    clang.CursorKind.BREAK_STMT,
    clang.CursorKind.RETURN_STMT,
    clang.CursorKind.GOTO_STMT,
    clang.CursorKind.CONTINUE_STMT,
}

class MissingBreak(Rule):
    rule_id = "MISSING_BREAK"
    description = "Possible fall-through in switch"

    def __init__(self):
        self.reported_cases = set()

    def reset(self):
        self.reported_cases.clear()


    def visit(self, node, scope=None):
        if node.kind != clang.CursorKind.CASE_STMT:
            return []

        loc = node.location
        if (loc.line, loc.column) in self.reported_cases:
            return []

        stmts = list(node.get_children())
        if not stmts:
            return []

        last_stmt = stmts[-1]

        if last_stmt.kind not in BREAK_TERMINATORS and last_stmt.kind not in (
            clang.CursorKind.CASE_STMT,
            clang.CursorKind.DEFAULT_STMT,
        ):
            self.reported_cases.add((loc.line, loc.column))
            return [Issue(self.rule_id,
                          "case appears to fall through – add break?",
                          loc.line, loc.column)]
        return []

    
class UninitializedVar(Rule):
    rule_id = "UNINITIALIZED_VAR"
    description = "Variable used before initialization"

    def __init__(self):
        self.reported = set()

    def reset(self):
        self.reported.clear()


    def visit(self, node, scope=None):
        issues = []

        if node.kind == clang.CursorKind.DECL_REF_EXPR:
            if scope:
                sym = scope.lookup(node.spelling)
                if sym and not sym.is_initialized:
                    loc = node.location
                    key = (node.spelling, loc.line, loc.column)
                    if key not in self.reported:
                        self.reported.add(key)
                        issues.append(Issue(self.rule_id,
                                            f"Variable '{node.spelling}' used before initialization",
                                            loc.line, loc.column))

        elif node.kind == clang.CursorKind.BINARY_OPERATOR:
            children = list(node.get_children())
            if len(children) == 2:
                left, right = children
                if left.kind == clang.CursorKind.DECL_REF_EXPR:
                    if scope:
                        scope.initialize(left.spelling)

        return issues


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    src_file = sys.argv[1]
    json_out = None
    if len(sys.argv) >= 4 and sys.argv[2] == "--json":
        json_out = Path(sys.argv[3])

    index = clang.Index.create()
    tu = index.parse(src_file, args=["-std=c11"])

    analyzer = Analyzer()
    
    analyzer.register(MissingBreak())
  
    analyzer.register(UninitializedVar())
  
    analyzer.register(ConstantCondition())
  
  
    analyzer.register(EmptyBody())
    
    analyzer.analyze(tu)

    if analyzer.issues:
        print(f"Issues found ({len(analyzer.issues)}):")
        for iss in analyzer.issues:
            print("  ", iss)
    else:
        print("No issues found.")

    
    if json_out:
        json_out.write_text(json.dumps([i.as_dict() for i in analyzer.issues], indent=2))
        print(f"Results written to {json_out}")

if __name__ == "__main__":
    main()