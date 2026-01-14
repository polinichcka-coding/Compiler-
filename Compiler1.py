import re #module for regular expressions
import sys

class Token:
    def __init__(self, type, value):
        self.type=type #eg number, name, etc
        self.value=value #string value

    def representation(self):
        #represent tokens for analyzing
        return f"Token({self.type}, {self.value})"

#broke into lexems
class Lexical_analyzer:
    def __init__(self, text):
        self.text=text #string to tokenize

    def tokenize(self):
        tokens_types=[
            ('number', r'[+-]?(\d+(\.\d*)?|\.\d+)(e[+-]?\d+)?'),
            ('name', r'[a-zA-Z]\w*'),
            ('leftpar', r'\('),
            ('rightpar', r'\)'),
            ('comma', r','),
            ('comment', r'/\*.*?\*/'),
            ('skip', r'[ \t\n]+'),
            ('others', r'.')
        ]

        #Used AI for understanding regex working
        #We use regex to split the input text into tokens
        #Every token type has its own regex pattern
        #We combine patterns with 'or'('|') 
        #It allows a single pass through text can match any type of token
        #Groups (?P<{name}>{pattern}) are used when we know
        #that we have match in types
        patterns=[]
        for name, pattern in tokens_types:
            named_pattern=f"(?P<{name}>{pattern})"
            patterns.append(named_pattern)
        regex = '|'.join(patterns)

        token = [] #stores tokens that are recognised
        for match in re.finditer(regex, self.text):
            token_type = match.lastgroup #name of group matched
            token_value = match.group() #string matched

            if token_type in ('skip', 'comment'):
                continue
            elif token_type in('others'):
                raise SyntaxError(f"Unknown symbol: {token_value}")
            else:
                token.append(Token(token_type, token_value)) #create Token object and add to list

        return token

#Class node for abstract tree
class Node:
    pass

#Number that we can have
class NumberNode(Node):
    def __init__(self, value):
        self.value = value #stores number as string

#Node of function
#name - name of function
#args - list of arguments
class FunctionNode(Node):
    def __init__(self, name, args):
        self.name = name
        self.args = args

    
#parse tree construction/parser
class Syntax_analyzer:
    def __init__(self, tokens):
        self.tokens=tokens
        self.position=0 #current position

    #current token without advancing
    def current(self):
        if self.position<len(self.tokens):
            return self.tokens[self.position]
        return None
    
    #take current token and move to next position
    def advance(self):
        tok=self.current()
        self.position+=1
        return tok
    
    #parsing
    def parse(self):
        return self.parse_expression()
    
    #parse one expression(number/function)
    def parse_expression(self):
        tok=self.current()
        if tok.type=='number':
            return NumberNode(self.advance().value)
        elif tok.type=='name':
            return self.parse_function()
        else:
            raise SyntaxError("Unrecognisable token")
        
    #parse function with arguments
    def parse_function(self):
        name=self.advance().value
        self.advance() #skip '('
        args=[]

        if self.current() and self.current().type != 'rightpar':
            while True:
                args.append(self.parse_expression()) #parse each argument
                tok=self.current()
                if tok and tok.type=='comma':
                    self.advance() #skip comma
                else:
                    break

        self.advance() #skip ')'
        return FunctionNode(name, args)

#abstract tree
class Semantic_analyzer:
    def __init__(self, tree):
        self.tree=tree #ast root

    #validate all ast
    def validate(self):
        self.check(self.tree)

    def check(self, node):
        #number - nothing(always valid)
        if isinstance(node, NumberNode):
            return
        
        #function - check
        elif isinstance(node, FunctionNode):
    #expect number of arguments for functions
            rules={
                'add':2, 'sub':2, 'mul':2,
                'div':2, 'mod':2, 'pow':2,
                'tern':3
            }
            if node.name not in rules:
                raise ValueError("Unrecognisable function: "+node.name)
            
            expected = rules[node.name]
            if len(node.args) != expected: 
                raise ValueError(f"Function {node.name} expects {expected} but receives {len(node.args)}")
            
            #check every elements
            for arg in node.args:
                self.check(arg)
#optimize code
class Optimizer:
    def __init__(self, tree):
        self.tree=tree
    
    def optimize(self):
        return self.optimized_node(self.tree)

    def optimized_node(self, node):
        #don't opimize numbers
        if isinstance(node, NumberNode):
            return node
        
        #optimize function
        elif isinstance(node, FunctionNode):
            optimized_args = []
            for arg in node.args:
                optimized_arg = self.optimized_node(arg)
                optimized_args.append(optimized_arg)
            name = node.name

            #for addition(1+0=0/0+1=1)
            if name=='add':
                #condition if one of number is 0
                if isinstance(optimized_args[0], NumberNode) and optimized_args[0].value=='0':
                    return optimized_args[1]
                elif isinstance(optimized_args[1], NumberNode) and optimized_args[1].value=='0':
                    return optimized_args[0]
            
            #for multiplication
            if name=='mul':
                #condition if one of number is 0 or 1
                if isinstance(optimized_args[0], NumberNode):
                    if optimized_args[0].value == '1':
                        return optimized_args[1]
                    if optimized_args[0].value == '0':
                        return NumberNode("0")
                if isinstance(optimized_args[1], NumberNode):
                    if optimized_args[1].value == '1':
                        return optimized_args[0]
                    if optimized_args[1].value == '0':
                        return NumberNode("0")
                    
            return FunctionNode(name, optimized_args)
    
#optimized code to target program 
class CodeGenerator:
    def __init__(self, ast):
        self.ast = ast

         #invert function name to symbol
        self.op_map = {
            'add': '+', 'sub': '-', 'mul': '*',
            'div': '/', 'mod': '%', 'pow': '^'
        }

        #higher number = higher precedence
        self.precedence = {
            'tern': 1,
            'add': 2, 'sub': 2,
            'mul': 3, 'div': 3, 'mod': 3,
            'pow': 4
        }

        #associativity
        self.assoc = {
            'tern': 'right',
            'pow': 'right',
            'add': 'left', 'sub': 'left',
            'mul': 'left', 'div': 'left', 'mod': 'left'
        }

    def generate(self):
        return self._generate_expr(self.ast)

    def _generate_expr(self, node):
        if isinstance(node, NumberNode):
            return node.value

        if isinstance(node, FunctionNode):
            name = node.name
            args = node.args

            #ternary operator
            if name == 'tern':
                cond = self._wrap(args[0], 1, 'right')
                true_expr = self._wrap(args[1], 1, 'right')
                false_expr = self._wrap(args[2], 1, 'right')
                return f"{cond}?{true_expr}:{false_expr}"

            #binary operators
            op = self.op_map[name]
            prec = self.precedence[name]
            assoc = self.assoc[name]

            left = self._wrap(args[0], prec, assoc, is_left=True)
            right = self._wrap(args[1], prec, assoc, is_left=False)
            return f"{left} {op} {right}"

        #decide whether we need parentheses
    def _wrap(self, child, parent_prec, parent_assoc, is_left=True):
        if isinstance(child, NumberNode):
            return child.value

        if isinstance(child, FunctionNode):
            expr = self._generate_expr(child)

            # skip parentheses for nested ternary
            if child.name == 'tern' and getattr(self.ast, 'name', None) == 'tern':
                return expr  

            child_prec = self.precedence[child.name]
            child_assoc = self.assoc[child.name]

            # decide if we need parentheses
            need_parens = False

            #priority lower - don't need 
            if child_prec < parent_prec:
                need_parens = True

            # same - associativity
            elif child_prec == parent_prec:
                if (parent_assoc == 'left' and not is_left) or (parent_assoc == 'right' and is_left):
                    need_parens = True

            #priority of child os higher
            #using of AI for clarifing if we need brackets and if yes for what purpose
            elif child_prec > parent_prec and parent_prec in (2, 3):  # add/sub/mul/div/mod
                need_parens = True

            return f"({expr})" if need_parens else expr

#summing up
def compiler(text):
    try:
        lexer = Lexical_analyzer(text)
        tokens = lexer.tokenize()

        parser = Syntax_analyzer(tokens)
        ast = parser.parse()

        semantic = Semantic_analyzer(ast)
        semantic.validate()

        optimizer = Optimizer(ast)
        optimized_ast = optimizer.optimize()

        codegen = CodeGenerator(optimized_ast)
        final_expression = codegen.generate()

        return final_expression
    
    except Exception as e:
            return f"Mistake: {e}"    
        
#console
if __name__ == "__main__":
    for line in sys.stdin:
        user_input = line.strip()
        if user_input:
            result = compiler(user_input)
            print("Expression:", user_input)
            print("Result:", result)
            print()