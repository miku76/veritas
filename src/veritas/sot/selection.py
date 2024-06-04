from loguru import logger
from anytree import AnyNode, PostOrderIter, search
from boolean_parser import parse as boolean_parser
from boolean_parser.actions.boolean import BoolAnd, BoolOr
from benedict import benedict

# veritas
from veritas.tools import tools
from veritas.sot import sot
from veritas.sot import queries


class Selection(object):
    """class to select data from nautobot

    This class is used to query nautobot. The syntax is comparable to SQL, where you have the three components:
    
        - SELECT
        - FROM
        - WHERE

    In addition, graphql queries can also be made with this class.

    Parameters
    ----------
    sot : sot
        the sot object
    values : string | list
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

    def __init__(self, sot:sot, select:tuple[list|str]) -> None:
        self._sot = sot
        self._using = set()

        self._node_id = 0
        self._cf_types = None
        self._transform = []

        # set limit and offset to use pagination
        self._limit = 0
        self._offset = 0

        # everything we need to join two tables
        self._join = None
        self._on = None
        self._left_table = None
        self._left_identifier = None
        self._right_table = None
        self._right_identifier = None

        # we have two modes sql and gql
        self._mode = "sql"

        # set selected values
        logger.debug(f'type of select: {type(select)}')
        if isinstance(select, str):
            self._select = select.replace(' ','').split(',')
        elif isinstance(select, list):
            self._select = select

    def using(self, schema:str) -> None:
        """configures which data source to use

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
            logger.bind(extra="using").debug(f'using: {self._using} as {self._left_identifier}')
        else:
            self._using = self._left_table = self._left_identifier = schema
        return self

    def set(self, **kwargs) -> None:
        """set

        Parameters
        ----------
        **kwargs
            named parameter that are used to set values

        Returns
        -------
        obj : Selection
            Selection

        Notes
        -----
        - We implement a fluent syntax. This methods returns self
        """
        if 'limit' in kwargs:
            self._limit = kwargs.get('limit')
        if 'offset' in kwargs:
            self._offset = kwargs.get('offset')

        logger.bind(extra="set").trace(f'limit: {self._limit} offset: {self._offset}')
        return self

    def join(self, schema:str) -> None:
        """join two schemas

        See the 'where' method for an example.

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
            logger.bind(extra="join").debug(f'join: {self._join} as {self._right_identifier}')
        else:
            self._join = self._right_table = self._right_identifier = schema

        return self

    def on(self, column:str) -> None:
        """on

        See the 'where' method for an example

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
        logger.bind(extra="on").debug(f'on: {self._on}')
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
        logger.debug(f'setting mode to {mode}')
        self._mode = mode
        return self

    def transform(self, transform:list|str) -> None:
        """transform

        If 'transform' is set, the data received is transformed to a different format

        Parameters
        ----------
        transform : list | str
           str or list of strings how to transform the data

        Returns
        -------
        obj : Selection
            Selection
        
        Notes
        -----
        - We implement a fluent syntax. This methods returns self
        """
        logger.debug(f'setting transform to {transform}')
        if isinstance(transform, str):
            self._transform = [transform]
        else:
            self._transform = transform
        return self

    def where(self, *unnamed, **named) -> dict:
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
            """
            You can join two tables as follows:

            vlans = my_sot.select('vlans.vid, vlans.name, vlans.interfaces_as_tagged, devices.name, devices.platform') \
                            .using('nb.vlans as vlans') \
                            .join('nb.devices as devices') \
                            .on('vlans.interfaces_as_tagged[0].device.id = devices.id') \
                            .where('vlans.vid=100')

            """
            left_select = set()
            right_select = set('')

            # check if properties is empty
            if len(properties) == 0:
                properties = ''

            # split the on statement
            join_on = self._on.replace(' ','').split('=')
            join_on_left = join_on[0].replace(f'{self._left_identifier}.','',1)
            join_on_right = join_on[1].replace(f'{self._right_identifier}.','',1)

            # add fields we are joining on
            # maybe th user wants a subfield; check if . found and use left part
            left_select.add(join_on_left.split('.')[0])
            right_select.add(join_on_right.split('.')[0])
            logger.bind(extra="where").debug(f'join detected; left: {self._left_table} as {self._left_identifier}' \
                f' right: {self._right_table} as {self._right_identifier} using: {self._using}')

            # prepare left select statement
            left_select.add('id')
            for c in self._select:
                if c.startswith(self._left_identifier):
                    left_select.add(c.replace(f'{self._left_identifier}.',''))

            # now we prpare the right one
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

            logger.bind(extra="where").debug(f'left: {where_left} right: {where_right} ' \
                    f'left_select: {left_select} right_select: {right_select}')

            # we need the raw values from the result and not 'transformated' ones
            # save self._transform and set it to None
            transform = self._transform
            self._transform = []

            # now get the values of the two tables
            left_result = self._parse_sql_query(where_left, list(left_select), self._left_table)
            right_result = self._parse_sql_query(where_right, list(right_select), self._right_table)

            # last but not least join the two tables
            self._transform = transform
            joined_result = self._join_results(left_result, right_result, self._on, left_select, right_select)
            if self._transform:
                select_list = []
                for s in self._select:
                    select_list.append(s.replace(f'{self._left_identifier}.',''))
                return queries.transform_data(joined_result, self._transform, select=select_list)
            else:
                return joined_result
        else:
            if self._mode == "sql":
                return self._parse_sql_query(properties, self._select, self._using)
            else:
                return self._parse_gql_query(properties, self._select, self._using)

    # private methods

    def _parse_gql_query(self, expression:str, select:list, using:str) -> dict:
        """parse GraphQL mode query

        Querying using the GQL mode is simple. We just have to parse the expression and query the data
        """
        return self._sot.get.query(
            select=select, 
            using=using, 
            where=expression, 
            mode='gql',
            transform=self._transform)

    def _parse_sql_query(self, expression:str, select:list, using:str) -> dict:
        """parse query and return result as dict

        Querying using the SQL mode is more complex. We have to parse the expression and build a logical tree
        then we merge the values of the leafs (if possible) and query the tree
        Finally, we merge all the individual queries.

        Parameters
        ----------
        expression : str
            boolean expression as string
        select : list
            value to get from the query
        using : str
            name of table to use

        Returns
        -------
        dict
            result of the query
        """        
        logger.bind(extra="parse").debug(f'expression {expression}')

        # lets check if we have a logical operation
        found_logical_expression = False
        try:
            if len(expression) > 0:
                res = boolean_parser(expression)
                res.logicop
                # yes we have one ... parse it
                logger.bind(extra="parse").debug(f'logical expression found {expression}')
                found_logical_expression = True
        except Exception:
            logger.bind(extra="parse").debug(f'no logical operation found ... simple expression {expression}')

        if found_logical_expression:
            # first we have to build a logical tree. This is a tree of the logical expression
            # Then we condense this tree and query it
            self._node_id = 0
            logger.bind(extra="parse").debug('building logical tree')
            logical_tree = self._build_logical_tree(res)
            logger.bind(extra="parse").debug('condense logical tree')
            self._condense_tree(logical_tree)
            logger.bind(extra="parse").debug('query logical tree')
            self._query_logical_tree(logical_tree, select, using)
            response = logical_tree.root.response
        else:
            response = self._simple_sql_query(
                select=select,
                using=using,
                expression=expression)
        
        return response

    def _simple_sql_query(self, select:list, using:str, expression: tuple[list|dict|str]) -> dict:
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

        # look at the expression. 'where' must be a dict!
        # it is a list ... parse it and make a dict
        if isinstance(expression, list):
            logger.bind(extra="simple_sql").trace(f'expression {expression} is a list')
            if len(expression) == 0:
                where = default
            else:
                for p in expression:
                    if '=' in p:
                        key, value = p.split('=')
                        where = {key: value}
        elif isinstance(expression, dict):
            logger.bind(extra="simple_sql").trace('expression is dict.Leave it as it is.')
            where = expression
        elif '=' in expression:
            # or a string .... split it and make a dict
            logger.bind(extra="simple_sql").trace('expression is string and contains "="')
            key, value = expression.split('=')
            where = {key: value}
        else:
            # or we use the default value
            logger.bind(extra="simple_sql").trace('setting default value as expression')
            where = default

        return self._sot.get.query(
            select=select, 
            using=using, 
            where=where, 
            mode='sql', 
            transform=self._transform,
            limit=self._limit,
            offset=self._offset)

    def _build_logical_tree(self, res: dict) -> AnyNode:
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
            logger.bind(extra="build tree").trace(f'cond=\'{cond}\' parent={parent} node={node}')

            # set root of tree
            if not root:
                root = node
            if isinstance(cond, BoolAnd) or isinstance(cond, BoolOr):
                operator = 'or' if isinstance(cond, BoolOr) else 'and'
                node.operator = operator
                node.values = None
                for c in cond.conditions:
                    logger.bind(extra="build tree").trace(f'append to stack... operator={operator} condition={c}')
                    stack.append({'cond': c, 
                                  'parent': node})
            else:
                node.values=self._convert_expression(cond.data)
                node.operator = None
                logger.bind(extra="build tree").trace(f'convert expression... node.values={node.values}')
        return root

    def _convert_expression(self, expression:dict) -> dict:
        """convert boolean parse condition to dict"""
        field = expression.get('parameter')
        operator = expression.get('operator')
        value = expression.get('value')
        
        logger.bind(extra="convert").debug(f'field: {field} operator: {operator} value: {value}')
        if operator == '!=':
            return {f'{field}__ne': [value]}
        else:
            # equals
            return {field: [value]}

    def _condense_tree(self, root: AnyNode) -> None:
        """condense tree - single run"""

        # we need the custom field types
        # Text fields do not support [String] but Select fields do
        # so cf_net=net or cf_net=anothernet cannot be merged to one query
        self._refresh_cf_types()

        run = 1
        logger.bind(extra="condense").debug(f'condense run {run}')
        while self._merge_equal_properties(root):
            run += 1
            logger.bind(extra="condense").debug(f'condense run {run}')

    def _refresh_cf_types(self) -> None:
        # refresh custom field types       
        nb = self._sot.open_nautobot()
        self._cf_types = {}
        for t in nb.extras.custom_fields.all():
            self._cf_types[t.display] = {'type': str(t.type)}

    def _merge_equal_properties(self, root: AnyNode) -> bool:
        """merge query values

        Sometimes we have a logical expression like 'name=lab-01.local or name=lab-02.local'
        Such a query can be merged to 'name=['lab-01.local', 'lab-02.local']'

        Parameters
        ----------
        root : AnyNode
            the logical tree

        Returns
        -------
        something_condensed : bool
            some values were merged together

        Raises
        ------
        KeyError
            if a key is unknown eg. an unknown custom field
        """
        nodes = search.findall(root, filter_=lambda node: node.values is None)
        something_condensed = False

        # we only merge nodes that are leafs

        for node in nodes:
            if node.operator == 'or':
                if all(c.is_leaf for c in node.children):
                    logger.bind(extra="merge values").debug(f'id: {node.id} operator "or" and all childrens are leafs')
                    merged = {}
                    cf_type_supported = True
                    for c in node.children:
                        for key, value in c.values.items():
                            if key.startswith('cf_'):
                                key_withhout_cf = key.replace('cf_','')
                                # keys can have some modifiers like cf_net__ie
                                # we have to replace this modifier
                                key_withhout_cf = key_withhout_cf.split('__')[0]
                                # check if cf_type supports merging
                                # [String] is supported / string is not
                                if key_withhout_cf not in self._cf_types:
                                    logger.bind(extra="merge values").error(f'unknown key {key}; aborting')
                                    raise KeyError(f'unknown key {key}')
                                if self._cf_types.get(key_withhout_cf).get('type','') == 'Text':
                                    cf_type_supported = False
                        if c.values:
                             merged = self._merge_dicts(merged, c.values)
                    if len(merged) == 1 and cf_type_supported:
                        logger.bind(extra="merge values").debug(f'leafs can be merged to {merged}')
                        node.values = self._merge_dicts(node.values, merged) if node.values else merged
                        node.children = []
                        something_condensed = True
                    else:
                        logger.bind(extra="merge values").debug(f'leafs cannot be merged merged={merged} ' \
                                f' cf_type_supported={cf_type_supported}' \
                                f' len(merged)={len(merged)}')
            elif node.operator == 'and':
                if all(c.is_leaf for c in node.children):
                    logger.bind(extra="merge values").debug(f'id: {node.id} operator "and" and all childrens are leafs')
                    merged = {}
                    for c in node.children:
                        merged = self._merge_dicts(merged, c.values) if c.values else merged
                    node.values = self._merge_dicts(node.values, merged) if node.values else merged
                    node.children = []
                    node.operator = None
                    something_condensed = True

        return something_condensed

    def _merge_dicts(self, dict1: dict, dict2: dict) -> dict:
        """merge two dicts together

        Parameters
        ----------
        dict1 : dict
            first dict
        dict2 : dict
            second dict

        Returns
        -------
        dict
            merged dict
        """
        keys = set(dict1).union(dict2)
        no = []
        return dict((k, dict1.get(k, no) + dict2.get(k, no)) for k in keys)

    def _query_logical_tree(self, logical_tree:AnyNode, select:list, using: str) -> None:
        """query each leaf and merge data (depending on or and and)"""
        if 'id' not in select:
            select += ['id']
        # walk through tree; childrens first than the other nodes
        for node in PostOrderIter(logical_tree):
            logger.bind(extra="query lt").debug(f'id: {node.id} operator: {node.operator} leaf: {node.is_leaf}')
            if node.is_leaf:
                logger.bind(extra="query lt").debug(f'node is leaf; type(node.values) = {type(node.values)}')
                logger.bind(extra="query lt").trace(f'node.values={node.values}')
                values = {}
                for key,value in node.values.items():
                    # executing SQL query needs a string and not a list as where clause
                    # but boolean expressions returns a list
                    logger.bind(extra="query lt").debug(f'key={key} value={value} type(value)={type(value)}')
                    if isinstance(value, list) and len(value) == 1:
                        values[key] = value[0]
                    else:
                        values[key] = value
                node.response = self._sot.get.query(select=select,
                                                    using=using,
                                                    where=values,
                                                    mode='sql',
                                                    transform=self._transform)
                logger.bind(extra="query lt").trace(f'node.response={node.response}')
            else:
                # have a look at the children and do the logical operation
                if node.operator == 'or':
                    logger.bind(extra="query lt").debug('node.operator is or')
                    lists = []
                    for c in node.children:
                        lists.append(c.response)
                    node.response = self._get_items(lists)
                elif node.operator == 'and':
                    logger.bind(extra="query lt").debug('node.operator is and')
                    lists = []
                    for c in node.children:
                        lists.append(c.response)
                    node.response = self._get_items_with_equal_id(lists)

    def _get_items_with_equal_id(self, all_items:list) -> list:
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
    
    def _get_items(self, all_items:list) -> list:
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

    def _join_results(self, left:dict, right:dict, join_on:str, left_select:str, right_select:str) -> list:
        """join left and right table"""
        join_on_list = self._on.replace(' ','').split('=')
        left_id = join_on_list[0].replace(f'{self._left_identifier}.','',1)
        right_id = join_on_list[1].replace(f'{self._right_identifier}.','',1)

        logger.bind(extra="join result").debug(f'join tables on left: {left_id} right: {right_id}')
        logger.bind(extra="join result").debug(f'left_select: {left_select}')
        logger.bind(extra="join result").debug(f'right_select: {right_select}')

        # print(json.dumps(left, indent=4))
        # print()
        # print(json.dumps(right, indent=4))
        # print('-----')
        result = []
        for left_data in left:
            l_values = benedict(left_data, keyattr_dynamic=True)
            for right_data in right:
                r_values = benedict(right_data, keyattr_dynamic=True)
                try:
                    left_value = l_values[left_id]
                    right_value = r_values[right_id]
                except KeyError:
                    continue
                if left_value == right_value:
                    new_right = {self._right_identifier: r_values}
                    l_values.update(new_right)
                    result.append(dict(l_values))
    
        return result
