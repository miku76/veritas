from loguru import logger
from anytree import AnyNode, PostOrderIter, search
from boolean_parser import parse as boolean_parser
from boolean_parser.actions.boolean import BoolAnd, BoolOr

# veritas
from veritas.tools import tools
from veritas.sot import sot


class Selection(object):
    """class to select data from nautobot

    This class is used to query nautobot. The syntax is comparable to SQL, where you have a SELECT a FROM and a WHERE clause.
    In addition, graphql queries can also be made with this class.

    Parameters
    ----------
    sot : sot
        the sot object
    values : string or list of strings
        the values to select

    Examples
    --------
    >>> # get id and hostname of a device
    >>> sot.select('id, hostname') \\
    >>>    .using('nb.devices') \\
    >>>    .where('name=lab.local')

    >>> # get all hosts of two locations
    >>> sot.select('hostname') \\
    >>>    .using('nb.devices') \\
    >>>    .where('location=default-site or location=site_1')

    """

    # we cache the queries if we have logical expressions
    # because we get a list of hostnames using the expression
    # and then get return the cahced values
    query_cache = {}

    def __init__(self, sot:sot, *values) -> None:
        self._sot = sot
        self._using = set()

        self._normalize = False
        self._node_id = 0
        self.__cf_types = None

        # everything we need to join two tables
        self._join = None
        self._on = None
        self._left_table = None
        self._left_identifier = None
        self._right_table = None
        self._right_identifier = None

        # we have two modes sql and gql
        self._mode = "sql"

        # set values
        if len(values) > 1:
            self._select = []
            for v in values:
                self._select.append(v)
        else:
            for v in values:
                if isinstance(v, str):
                    self._select = v.replace(' ','').split(',')
                elif isinstance(v, list):
                    self._select = v

    def using(self, schema:str) -> None:
        """_summary_

        Parameters
        ----------
        schema : str
            which schema to use

        Returns
        -------
        obj : Selection
            Selection
        
        Notes
        -----
        - We implement a fluent syntax. This methods returns self

        """
        # check if "table as id" was used
        # in this case we have a join
        if ' as ' in schema:
            s = schema.split(' as ')
            self._using = schema = s[0]
            self._left_table = self._using
            self._left_identifier = s[1]
        else:
            self._using = self._left_table = self._left_identifier = schema
        return self

    def join(self, schema:str) -> None:
        """join two schemas

        Parameters
        ----------
        schema : str
            name of the two graphql schemas

        Returns
        -------
        obj : Selection
            Selection

        Notes
        -----
        - We implement a fluent syntax. This methods returns self
        """
        if ' as ' in schema:
            s = schema.split(' as ')
            self._join = schema = s[0]
            self._right_table = self._join
            self._right_identifier = s[1]
        else:
            self._join = self._right_table = self._right_identifier = schema

        return self

    def on(self, column:str) -> None:
        """on

        Parameters
        ----------
        column : str
            name of the columns separeted by '='

        Returns
        -------
        obj : Selection
            Selection

        Notes
        -----
        - We implement a fluent syntax. This methods returns self
        """        
        self._on = column
        return self

    def mode(self, mode:str) -> None:
        """mode

        Parameters
        ----------
        mode : str
            which mode (sql or gql)

        Returns
        -------
        obj : Selection
            Selection
        
        Notes
        -----
        - We implement a fluent syntax. This methods returns self
        """
        logger.debug('setting mode to {mode}')
        self._mode = mode
        return self

    def where(self, *unnamed, **named):
        """where

        Parameters
        ----------
        *unnamed
            unnamed parameter that are used as 'where' clause
        **named
            named parameter that are used as 'where' clause

        Returns
        -------
        result : dict
            the result of the query
        
        Notes
        -----
        by calling this method the query is executed and the result returned

        Examples
        --------
        >>> devices = sot.select('id, hostname') \\
        ...              .using('nb.devices') \\
        ...              .where('name=lab.local')

        """        
        properties = tools.convert_arguments_to_properties(*unnamed, **named)
        logger.debug(f'query: values {self._select} using: {self._using} where {properties} mode: {self._mode}')

        # is it a join operation
        if self._join:
            left_select = set()
            right_select = set('')

            # check if properties is empty
            if len(properties) == 0:
                properties = ''

            # split the on statement
            join_on = self._on.replace(' ','').split('=')
            join_left_row = join_on[0].replace(f'{self._left_identifier}.','',1)
            join_right_row = join_on[1].replace(f'{self._right_identifier}.','',1)
            # add fields we are joining on
            # maybe th user wants a subfield; check if . found and use left part
            left_select.add(join_left_row.split('.')[0])
            right_select.add(join_right_row.split('.')[0])

            # prepare left select statement
            left_select.add('id')
            for c in self._select:
                if c.startswith(self._left_identifier):
                    left_select.add(c.replace(f'{self._left_identifier}.',''))
            # does the same with the right one
            right_select.add('id')
            for c in self._select:
                if c.startswith(self._right_identifier):
                    right_select.add(c.replace(f'{self._right_identifier}.',''))

            # adjust the where clause (properties)
            where_splits = properties.replace(' ','').split(',')
            where_left = []
            where_right = []
            for w in where_splits:
                if w.startswith(self._left_identifier):
                    where_left.append(w.replace(f'{self._left_identifier}.','',1))
                if w.startswith(self._right_identifier):
                    where_right.append(w.replace(f'{self._right_identifier}.','',1))

            logger.debug(f'join detected; left: {self._left_table}/{self._left_identifier}' \
                f' right: {self._right_table}/{self._right_identifier} using: {self._using}')
            logger.debug(f'left_select: {left_select} left_where: {where_left}' \
                f' right_select: {right_select} right_where: {where_right}')

            left_result = self._parse_query(where_left, list(left_select), self._left_table)
            right_result = self._parse_query(where_right, list(right_select), self._right_table)
            return self._join_results(left_result, right_result, self._on)
        else:
            if self._mode == "sql":
                return self._parse_sql_query(properties, self._select, self._using)
            else:
                return self._parse_gql_query(properties, self._select, self._using)

    # private methods

    # GQL mode 
    def _parse_gql_query(self, expression, select, using):
        """parsw GraphQL mode query"""
        return self._sot.get.query(select=select, using=using, where=expression, mode='gql')

    # SQL mode below

    def _parse_sql_query(self, expression, select, using):
        logger.debug(f'expression {expression} ({len(expression)})')
        # lets check if we have a logical operation
        found_logical_expression = False
        try:
            if len(expression) > 0:
                res = boolean_parser(expression)
                res.logicop
                # yes we have one ... parse it
                logger.debug(f'logical expression found {expression}')
                found_logical_expression = True
        except Exception:
            logger.debug(f'no logical operation found ... simple call {expression}')

        if found_logical_expression:
            self._node_id = 0
            logical_tree = self._build_logical_tree(res)
            self._condense_tree(logical_tree)
            self._query_logical_tree(logical_tree, select, using)
            response = logical_tree.root.response
        else:
            response = self._simple_sql_query(expression, select, using)
        
        return response

    def _simple_sql_query(self, properties, select, using):
        """return data of simple SQL queries
           This is a query that runs independently, so no additional data is required.
        """

        if 'nb.ipaddresses' in using:
            default={'address': ''}
        elif 'nb.changes' in using:
            default={'time__gt': ''}
        elif 'nb.prefixes' in using:
            default={'prefix': ''}
        else:
            default={'name': ''}

        if isinstance(properties, list):
            if len(properties) == 0:
                where = default
            else:
                for p in properties:
                    if '=' in p:
                        key, value = p.split('=')
                        where = {key: value}
        elif '=' in properties:
            key, value = properties.split('=')
            where = {key: value}
        else:
            where = default

        return self._sot.get.query(select=select, using=using, where=where, mode='sql')

    def _build_logical_tree(self, res):
        """parse logical expression and build tree"""

        id = -1
        root = None
        stack = [{'cond': res, 
                  'parent': None}]

        while (stack):
            id += 1
            s = stack.pop()
            cond = s.get('cond')
            parent = s.get('parent')
            node = AnyNode(id=id, parent=parent)
            # set root of tree
            if not root:
                root = node
            if isinstance(cond, BoolAnd) or isinstance(cond, BoolOr):
                operator = 'or' if isinstance(cond, BoolOr) else 'and'
                node.operator = operator
                node.values = None
                # node.where = None
                for c in cond.conditions:
                    stack.append({'cond': c, 
                                  'parent': node})
            else:
                node.values=self._convert_expression(cond.data)
                node.operator = None
        return root

    def _convert_expression(self, expression):
        """convert boolean parse condition to dict"""
        field = expression.get('parameter')
        operator = expression.get('operator')
        value = expression.get('value')
        
        logger.debug(f'field: {field} operator: {operator} value: {value}')
        if operator == '!=':
            return {f'{field}__ne': [value]}
        else:
            # equals
            return {field: [value]}

    def _condense_tree(self, root):
        """condense tree - single run"""

        # we need the custom field types
        # Text fields do not support [String] but Select fields do
        # so cf_net=net or cf_net=anothernet cannot be merged to one query
        self._refresh_cf_types()

        run = 1
        logger.debug(f'condense run {run}')
        while self._condense_single_run(root):
            run += 1
            logger.debug(f'condense run {run}')

    def _refresh_cf_types(self):
        nb = self._sot.open_nautobot()
        self.__cf_types = {}
        for t in nb.extras.custom_fields.all():
            self.__cf_types[t.display] = {'type': str(t.type)}

    def _condense_single_run(self, root):
        nodes = search.findall(root, filter_=lambda node: node.values is None)
        something_condensed = False
        for node in nodes:
            if node.operator == 'or':
                if all(c.is_leaf for c in node.children):
                    logger.debug(f'id: {node.id} operator "or" and all childrens are leafs')
                    merged = {}
                    cf_type_supported = True
                    for c in node.children:
                        for key, value in c.values.items():
                            if key.startswith('cf_'):
                                # check if cf_type supports merging
                                if self.__cf_types.get(key.replace('cf_','')).get('type','') == 'Text':
                                    cf_type_supported = False
                        if c.values:
                             merged = self._merge_dicts(merged, c.values)
                    if len(merged) == 1 and cf_type_supported:
                        logger.debug(f'leafs can be merged to {merged}')
                        # f = list(merged.keys())
                        node.values = self._merge_dicts(node.values, merged) if node.values else merged
                        node.children = []
                        something_condensed = True
            elif node.operator == 'and':
                if all(c.is_leaf for c in node.children):
                    logger.debug(f'id: {node.id} operator "and" and all childrens are leafs')
                    merged = {}
                    for c in node.children:
                        merged = self._merge_dicts(merged, c.values) if c.values else merged
                    # f = list(merged.keys())
                    node.values = self._merge_dicts(node.values, merged) if node.values else merged
                    node.children = []
                    node.operator = None
                    something_condensed = True

        return something_condensed

    def _merge_dicts(self, dict1, dict2):
        keys = set(dict1).union(dict2)
        no = []
        return dict((k, dict1.get(k, no) + dict2.get(k, no)) for k in keys)

    def _query_logical_tree(self, logical_tree, select, using):
        """query each leaf and merge data (depending on or and and)"""
        if 'id' not in select:
            select += ['id']
        # walk through tree; childrens first than the other nodes
        for node in PostOrderIter(logical_tree):
            logger.debug(f'id: {node.id} operator: {node.operator} leaf: {node.is_leaf}')
            if node.is_leaf:
                node.response = self._sot.get.query(select=select,
                                                    using=using,
                                                    where=node.values)
            else:
                # have a look at the children and do the logical operation
                if node.operator == 'or':
                    lists = []
                    for c in node.children:
                        lists.append(c.response)
                    node.response = self._get_items(lists)
                elif node.operator == 'and':
                    lists = []
                    for c in node.children:
                        lists.append(c.response)
                    node.response = self._get_items_with_equal_id(lists)

    def _get_items_with_equal_id(self, all_items):
        """returns a list of items with equal id"""

        # 1. case: we have only one sublist; return result
        if len(all_items) == 1:
            return all_items[0]
        
        result = []
        logger.debug(f'merging {len(all_items)} lists to one')
        # 2. we have multiple lists
        # get first list and check which item is in this list and all other lists
        anchor = all_items[0]
        # others is a list of lists
        others = all_items[1:]
        for ac in anchor:
            id = ac.get('id', -1)
            for o in others[0]:
                if o.get('id') == id:
                    result.append(o)
        return result
    
    def _get_items(self, all_items):
        """returns all values without duplicates"""

         # 1. case: we have only one sublist; return result
        if len(all_items) == 1:
            return all_items[0]
        
        result = all_items[0]
        # 2. we have multiple lists
        # check if item is already in result and add it if not
        others = all_items[1:]
        for o in others:
            for x in o:
                id = x.get('id',-1)
                # check if id is in result
                if not any(d['id'] == id for d in result):
                    logger.debug(f'add {id} to result')
                    result.append(x)
                else:
                    logger.debug(f'{id} is duplicate')
        
        return result

    def _join_results(self, left, right, join_on):
        """join left and right table"""
        join_on_list = self._on.replace(' ','').split('=')
        left_id = join_on_list[0].replace(f'{self._left_identifier}.','',1)
        right_id = join_on_list[1].replace(f'{self._right_identifier}.','',1)
        logger.debug(f'join tables on left: {left_id} right: {right_id}')

        # print(json.dumps(left, indent=4))
        # print()
        # print(json.dumps(right, indent=4))
        # print('-----')
        result = []
        for x in left:
            value = self._get_value_from_dict(x, left_id.split('.'))
            if value:
                # check if value exists in right table
                for r in right:
                    r_val = self._get_value_from_dict(r, right_id.split('.'))
                    if r_val == value:
                        x.update(r)
                        result.append(x)
        return result
    
    def _get_value_from_dict(self, dictionary, keys):
        if dictionary is None:
            return None

        nested_dict = dictionary

        for key in keys:
            try:
                nested_dict = nested_dict[key]
            except KeyError:
                return None
            except IndexError:
                return None
            except TypeError:
                # check if nested_dict is a list
                if isinstance(nested_dict, list):
                    # check if next key is in any list
                    for x in nested_dict:
                        if key in x:
                            return x[key]
                    return None
                else:
                    return nested_dict

        return nested_dict
