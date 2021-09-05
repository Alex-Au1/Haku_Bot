import psycopg2, enum
from tools.string import StringTools
from typing import Dict, Any, List, Optional, Union, Callable

DATABASE = "my_database"
USERNAME = "my_username"
PASSWORD = "my_password"
HOST = "the_host_of_my_database"
PORT = "some_port"

STRING_QUOTE = "\'"
REPLACEMENTS = {STRING_QUOTE: "\""}


# DbItem: An item being tracked by the database
class DbItem():
    def __init__(self, name: str, index: int, table: str, col: str):
        self.name = name
        self.index = index
        self.table = table
        self.col = col


# SelectType: Different ways for arranging selected data from the database
class SelectType(enum.Enum):
    Select = "select"
    Formatted = "formatted"
    List = "list"
    Hash = "has"


#class for manipulating files
class Database:
    AND = "and"
    OR = "or"

    #method for connecting to the database
    @classmethod
    def connect(cls):
        conn = psycopg2.connect(database = DATABASE, user = USERNAME, password = PASSWORD, host = HOST, port = PORT)
        return conn


    # format_str(str) formats a string to updated into the database
    @classmethod
    def format_str(cls, str: str):
        if (str[0] == STRING_QUOTE and str[-1] == STRING_QUOTE):
            partial_str = str[1:-1]
            partial_str = partial_str.replace(STRING_QUOTE, REPLACEMENTS[STRING_QUOTE])
            str = str[0] + partial_str + str[-1]

        return str


    # add_conditions(sql_query, conditions, connective, add_where)
    #   Adds conditions to an SQL query
    @classmethod
    def add_conditions(cls, sql_query: str, conditions: Dict[str, str], connective: str = "and", add_where: bool = True) -> str:
        #add condition if applicable
        counter = 0

        for c in conditions:
            if (counter == 0):
                if (add_where):
                    sql_query += "WHERE "
                sql_query += f'{c}={conditions.get(c)}'
            elif (connective == cls.AND):
                sql_query += f' AND {c}={conditions.get(c)}'
            elif (connective == cls.OR):
                sql_query += f' OR {c}={conditions.get(c)}'

            counter += 1

        return sql_query


    # sop(sql_query, conditions, add_where) Returns the Sum of Products statement condition
    @classmethod
    def sop(cls, sql_query: str, conditions: Dict[str, str], add_where: bool = False) -> str:
        if (add_where):
            sql_query += "WHERE "

        counter = 0
        for c in conditions:
            current_product = cls.add_conditions("", c, add_where = False)
            current_product = f"({current_product})"

            if (not counter):
                sql_query += current_product
                counter += 1
            else:
                sql_query += f" OR {current_product}"

        return sql_query


    # select(columns, table, conditions, custom_command, custom_condition, connective)
    #   Selects data from the database as nested lists
    @classmethod
    def select(cls, columns: List[str], table: str,conditions: Optional[Dict[str, str]] = None,
               custom_command: Optional[str] = None, custom_condition: Optional[str] = None, connective: str = "and") -> List[List[Any]]:

        #if the user does not have a custom sql query
        if (custom_command is None):
            #sql query for tables to be selected
            column_selection = ""

            if (len(columns) == 1):

                #if user selects all columns
                if (columns[0] == "*"):
                    column_selection += "*"
                else:
                    column_selection += columns[0]

            else:
                for i in range(len(columns)):
                    current_column = cls.format_str(columns[i])
                    if (i == 0):
                        column_selection += current_column
                    else:
                        column_selection += f", {current_column}"

            #sql query
            sql_query = f'SELECT {column_selection} from public."{table}"'


            #add conditions if applicable
            if (conditions is not None):
                sql_query = cls.add_conditions(sql_query, conditions, connective = connective)
            elif (custom_condition is not None):
                sql_query += ("WHERE " + custom_condition)

        #if the user chooses to have a custom sql query
        else:
            sql_query = custom_command

        #create connection
        conn = cls.connect()

        #select the tables
        cur = conn.cursor()
        cur.execute(sql_query)

        #copy the data into an array
        rows = cur.fetchall()

        #close the connection
        conn.close()

        #return the array
        return rows


    # formatted_select(lo_col_names, columns, table, conditions, custom_command)
    #   selects certain data from the database and formats each entry as
    #   a dictionary
    @classmethod
    def formatted_select(cls, lo_col_names: List[str], columns: List[str], table: str, conditions: Optional[Dict[str, str]] = None,
                         custom_command: Optional[Dict[str, str]] = None, custom_condition: Optional[str] = None,
                         connective: str = "and") -> List[Dict[str, Any]]:
        result_arr = cls.select(columns, table, conditions,custom_command, custom_condition = custom_condition, connective = connective)

        no_of_entries = len(result_arr)
        no_of_columns = len(lo_col_names)
        result_lst = []

        for i in range(no_of_entries):
            current_data = {}

            for j in range(no_of_columns):
                current_data[lo_col_names[j]] = result_arr[i][j]
            result_lst.append(current_data)

        return result_lst


    # formatted_select(column, table, conditions, custom_command, connective)
    #   selects a column from the database and formatted it to a single list
    @classmethod
    def list_select(cls, column: str, table: str, conditions: Optional[Dict[str, str]] = None,
                    custom_command: Optional[str] = None, custom_condition: Optional[str] = None, connective: str = "and") -> List[Any]:
        result_arr = cls.select([column], table, conditions,custom_command, custom_condition = custom_condition, connective = connective)

        no_of_entries = len(result_arr)
        result_lst = []
        for i in range(no_of_entries):
            result_lst.append(result_arr[i][0])

        return result_lst


    # hash_select(cls, key_index, lo_col_names, columns, table, conditions, custom_command, custom_condition, connective)
    #   selects a column from the database and formatted as nested dictionaries
    @classmethod
    def hash_select(cls, key_index: int, lo_col_names: List[str], columns: List[str], table: str, conditions: Optional[Dict[str, str]] = None,
                    custom_command: Optional[str] = None, custom_condition: Optional[str] = None, connective: str = "and") -> Dict[str, Dict[str, Any]]:
        result_arr = cls.select(columns, table, conditions,custom_command, custom_condition = custom_condition, connective = connective)

        no_of_entries = len(result_arr)
        no_of_columns = len(lo_col_names)
        result_dict = {}

        for i in range(no_of_entries):
            current_data = {}

            for j in range(no_of_columns):
                current_data[lo_col_names[j]] = result_arr[i][j]
            result_dict[result_arr[i][key_index]] = current_data

        return result_dict


    # insert(data, table, conditions, custom_command) Inserts data into the database
    @classmethod
    def insert(cls, data: Dict[str, str], table: str, conditions: Optional[Dict[str, str]] = None, custom_command: Optional[str] = None):
        #columns to be inserted
        column_selection = ""

        #values for each column
        column_value_selection = ""

        data_counter = 0

        for d in data:
            current_column = cls.format_str(data[d])
            if (data_counter == 0):
                column_selection += d
                column_value_selection += current_column
            else:
                column_selection += f",{d}"
                column_value_selection += f",{current_column}"

            data_counter += 1

        #sql query
        sql_query = f'INSERT INTO public."{table}" ({column_selection}) VALUES ({column_value_selection})'

        #create connection
        conn = cls.connect()

        #select the tables
        cur = conn.cursor()
        cur.execute(sql_query)
        conn.commit()

        #close the connection
        conn.close()


    # update(data, table, conditions, custom_command)
    #   updates the data in the database
    @classmethod
    def update(cls, data: Dict[str, str], table: str, conditions: Optional[Dict[str, str]]=None, custom_command: Optional[str] = None):
        #columns to be updated
        column_update_selection = ""

        data_counter = 0

        for d in data:
            current_column = cls.format_str(data[d])
            if (data_counter == 0):
                column_update_selection += f"SET {d}={current_column}"
            else:
                column_update_selection += f", {d}={current_column}"

            data_counter += 1

        #sql query
        sql_query = f'UPDATE public."{table}" {column_update_selection}'

        #add conditions if applicable
        if (conditions is not None):
            sql_query = cls.add_conditions(sql_query, conditions)

        #create connection
        conn = cls.connect()

        #update the table
        cur = conn.cursor()
        cur.execute(sql_query)
        conn.commit()

        #close the connection
        conn.close()



    # delete(table, conditions) Deletes data from the database
    @classmethod
    def delete(cls, table: str, conditions: Dict[str, str]):
        #sql query
        sql_query = f'DELETE from public."{table}"'

        #add conditions
        sql_query = cls.add_conditions(sql_query, conditions)

        #create connection
        conn = cls.connect()

        #delete the specific row in the table
        cur = conn.cursor()
        cur.execute(sql_query)
        conn.commit()

        #close the connection
        conn.close()


    # in_table(cls, value, column, table) Determines if 'value' is in 'table'
    @classmethod
    def in_table(cls, value: Any, column: str, table: str) -> Optional[List[List[Any]]]:
        result = cls.select(["*"], f"{table}", {f"{column}":f"{value}"})
        if (result):
            return result
        else:
            return None


    # general_select(select_type, select_args, select_kwargs) Selects data
    #   from the database and format the data based from 'select_type'
    @classmethod
    def general_select(cls, select_type: SelectType, select_args: List[Any], select_kwargs: Dict[str, Any]) -> Union[List[List[Any]], List[Dict[str, Any]], Dict[str, Dict[str, Any]], List[Any]]:
        if (select_type == SelectType.Select):
            selected_result = cls.select(*select_args, **select_kwargs)
        elif (select_type == SelectType.Formatted):
            selected_result = cls.formatted_select(*select_args, **select_kwargs)
        elif (select_type == SelectType.List):
            selected_result = cls.list_select(*select_args, **select_kwargs)
        elif (select_type == SelectType.Hash):
            selected_result = cls.hash_select(*select_args, **select_kwargs)

        return selected_result


    # default_select(default_row_func, select_type, select_args, select_kwargs, default_func_args, default_func_kwargs)
    #   Selects data from the database and creates a new entry in the table if
    #   the selected data is not found
    @classmethod
    def default_select(cls, default_row_func: Callable[[...], Union[List[List[Any]], List[Dict[str, Any]],
                       Dict[str, Dict[str, Any]], List[Any]]], select_type: SelectType, select_args: List[Any],
                       select_kwargs: Dict[str, Any], default_func_args: List[Any], default_func_kwargs: Dict[str, Any]) -> Union[List[List[Any]], List[Dict[str, Any]], Dict[str, Dict[str, Any]], List[Any]]:
        selected_result = cls.general_select(select_type, select_args, select_kwargs)

        if (selected_result):
            return selected_result
        else:
            default_row_func(*default_func_args, **default_func_kwargs)
            selected_result = cls.general_select(select_type, select_args, select_kwargs)
            return selected_result
