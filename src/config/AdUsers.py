from dataclasses import dataclass, fields
from ldap3 import Server, Connection, ALL, SUBTREE
import sqlite3

@dataclass
class UserInfo:
    username: str
    groupname: str = None
    cn: str = None
    uid: int = None
    gid: int = None
    sid: str = None
    dn: str = None
    mail: str = None
    # groups: list[str]


@dataclass
class LdapConfig:
    HOST: str = "openldap"
    PORT: int = 389
    BASE_DN: str = None
    BIND_PW: str = None
    BIND_DN: str = None
    USER_BASE_RDN: str = None
    GROUP_BASE_RDN: str = None
    USER_FILTER: str = '(cn=*)'
    GROUP_FILTER: str = '(cn=*)'
    TLS = False
    USERNAME_ATTRIBUTE = 'uid'
    GROUPNAME_ATTRIBUTE = 'ou'

    @property
    def SERVER_URL(self) -> str:
        if self.HOST is None:
            raise ValueError("HOST is None")
        return '{PROTO}://{HOST}:{PORT}'.format(
            PROTO='ldaps' if self.TLS else 'ldap',
            HOST=self.HOST,
            PORT=self.PORT)

    @property
    def USER_BASE_DN(self) -> str:
        return self.get_dn_by_rdn(self.USER_BASE_RDN)

    @property
    def GROUP_BASE_DN(self) -> str:
        return self.get_dn_by_rdn(self.GROUP_BASE_RDN)

    def USER_BASIC_FILTER(self, username: str) -> str:
        return '({USERNAME_ATTRIBUTE}={username})'.format(username=username, USERNAME_ATTRIBUTE=self.USERNAME_ATTRIBUTE)

    def GROUP_BASIC_FILTER(self, groupname: str) -> str:
        return '({GROUPNAME_ATTRIBUTE}={groupname})'.format(GROUPNAME_ATTRIBUTE=self.GROUPNAME_ATTRIBUTE, groupname=groupname)

    def get_dn_by_rdn(self, rdn: str) -> str:
        base_dn = self.BASE_DN
        if rdn is None or rdn.strip() == '':
            return base_dn
        return '{RDN},{BASE}'.format(RDN=rdn, BASE=base_dn)

    def get_user_dn(self, username: str) -> str:
        return self.get_user_dn_ou(username, self.USER_BASE_DN, self.USERNAME_ATTRIBUTE)

    def get_group_dn(self, groupname: str) -> str:
        return self.get_group_dn_ou(groupname, self.GROUP_BASE_DN, self.GROUPNAME_ATTRIBUTE)

    def get_user_filter(self, username: str) -> str:
        USER_BASIC_FILTER = self.USER_BASIC_FILTER(username)
        if self.USER_FILTER is None or self.USER_FILTER.strip() == '':
            return USER_BASIC_FILTER
        return '(&({USER_BASIC_FILTER}){filter})'.format(USER_BASIC_FILTER=USER_BASIC_FILTER, filter=self.USER_FILTER)

    def get_group_filter(self, groupname: str) -> str:
        GROUP_BASIC_FILTER = self.GROUP_BASIC_FILTER(groupname)
        if self.GROUP_FILTER is None or self.GROUP_FILTER.strip() == '':
            return GROUP_BASIC_FILTER
        return '(&({GROUP_BASIC_FILTER}){filter})'.format(GROUP_BASIC_FILTER=GROUP_BASIC_FILTER, filter=self.GROUP_FILTER)

    @classmethod
    def get_user_dn_ou(cls, username: str, ou_dn: str, USERNAME_ATTRIBUTE: str = 'uid'):
        return '{USERNAME_ATTRIBUTE}={username},{OU_DN}'.format(username=username, USERNAME_ATTRIBUTE=USERNAME_ATTRIBUTE, OU_DN=ou_dn)

    @classmethod
    def get_group_dn_ou(cls, groupname: str, ou_dn: str, GROUPNAME_ATTRIBUTE: str = 'cn'):
        return '{GROUPNAME_ATTRIBUTE}={groupname},{OU_DN}'.format(GROUPNAME_ATTRIBUTE=GROUPNAME_ATTRIBUTE, groupname=groupname, OU_DN=ou_dn)

    def server(self) -> Server:
        return Server(host=self.HOST, port=self.PORT, use_ssl=self.TLS, get_info=ALL)

    def connect(self) -> Connection:
        if self.BIND_DN is None:
            raise ValueError("BIND_DN is None")
        elif self.BIND_PW is None:
            raise ValueError("BIND_PW is None")
        server = self.server()
        return Connection(server, self.BIND_DN, self.BIND_PW, auto_bind=True)


class MyAD:
    def __init__(self, ad: LdapConfig, base_uid: int = 1615200000) -> None:
        self.__ad_config = ad
        self.base_uid: int = base_uid
        self.__ad: Connection = None
        self.force_gid: int = None
        self.force_gname: str = None

    @property
    def ad_config(self) -> LdapConfig:
        return self.__ad_config

    @property
    def ad(self) -> Connection:
        return self.__ad

    def connect(self):
        """
        connect to ldap server. If already connected, do nothing.
        """
        if self.ad is None:
            self.__ad = self.ad_config.connect()

    def disconnect(self):
        """
        disconnect from ldap server. If already disconnected, do nothing.
        """
        if self.ad is not None:
            self.ad.unbind()
            self.__ad = None

    def get_user_sid(self, username: str) -> str:
        """
        get user sid by username.\n
        it search base on USER_BASE_DN and USER_BASIC_FILTER(username)
        """
        self.connect()
        BASI_USER_FILTER = self.ad_config.USER_BASIC_FILTER(username)
        self.ad.search(self.ad_config.USER_BASE_DN, BASI_USER_FILTER, SUBTREE, attributes=['objectSid'])
        if len(self.ad.entries) == 0:
            return None
        return self.ad.entries[0].objectSid.value

    def get_user_sid_uid(self, username: str) -> tuple[str, int]:
        """
        get user uid by username.\n
        it get sid by get_user_sid(username) and then convert it to uid by sid_to_uid(sid,base_uid)
        """
        sid = self.get_user_sid(username)
        if sid is None:
            return None, None
        return sid, self.sid_to_uid(sid, self.base_uid)

    def get_user_info(self, username: str) -> UserInfo:
        """
        get user info by username.\n
        it search base on USER_BASE_DN and USER_BASIC_FILTER(username)
        """
        self.connect()
        BASI_USER_FILTER = self.ad_config.USER_BASIC_FILTER(username)
        self.ad.search(self.ad_config.USER_BASE_DN, BASI_USER_FILTER, SUBTREE, attributes=['objectSid', 'cn', 'mail'])
        if len(self.ad.entries) == 0:
            return None
        entry = self.ad.entries[0]
        sid = entry.objectSid.value
        uid = self.sid_to_uid(sid, self.base_uid)
        cn = entry.cn.value
        mail = entry.mail.value if entry.mail is not None else None
        if self.force_gid is None:
            gid = uid
            groupname = username
        else:
            gid = self.force_gid
            groupname = self.force_gname
        return UserInfo(username=username,groupname=groupname, cn=cn, uid=uid,gid=gid, sid=sid, dn=entry.entry_dn, mail=mail)

    def get_user_info_all(self) -> list[UserInfo]:
        """
        get all user info.\n
        """
        self.connect()
        username_attr = self.ad_config.USERNAME_ATTRIBUTE
        self.ad.search(self.ad_config.USER_BASE_DN, self.ad_config.USER_FILTER, SUBTREE, attributes=['objectSid', 'cn', 'mail', username_attr])
        user_list:list[UserInfo] = [UserInfo(username=entry[username_attr].value, cn=entry.cn.value, uid=self.sid_to_uid(entry.objectSid.value, self.base_uid), sid=entry.objectSid.value, dn=entry.entry_dn, mail=entry.mail.value if entry.mail is not None else None) for entry in self.ad.entries]
        if self.force_gid is not None:
            for user in user_list:
                user.gid = self.force_gid 
                user.groupname = self.force_gname
        return user_list
    
    @classmethod
    def sid_to_uid(cls, sid: str, base_uid: int = 1615200000):
        """
        RID is the last part of SID, and it is the uid of user.\n
        """
        rid = int(sid.split('-')[-1])
        return base_uid + rid


class UserSql:
    def __init__(self, db: str):
        self.db_connect_info = db
        self.__sql: sqlite3.Connection = None
        self.__c: sqlite3.Cursor = None
        self.table: str = 'AD_USER'

    @property
    def cursor(self) -> sqlite3.Cursor:
        return self.__c

    @property
    def sql(self) -> sqlite3.Connection:
        return self.__sql

    def connect(self):
        """
        connect to sqlite database. If already connected, do nothing.
        """
        if self.__sql is not None:
            self.disconnect()
        self.__sql = sqlite3.connect(self.db_connect_info)
        self.__c = self.__sql.cursor()
        self.create_table()

    def disconnect(self):
        """
        disconnect from sqlite database. If already disconnected, do nothing.
        """
        if self.__sql is not None:
            self.__sql.close()
            self.__sql = None
            self.__c = None

    def create_table(self):
        """
        create table if not exists
        """
        # self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        # print(self.cursor.fetchall())
        check_table_query = f"SELECT count(name) FROM sqlite_master WHERE type='table' AND name='{self.table}';"
        # print(check_table_query)
        self.cursor.execute(check_table_query)
        result = self.cursor.fetchone()
        # print(result)
        if result[0] == 0:
            create_table_query = f"CREATE TABLE IF NOT EXISTS {self.table} (id INTEGER PRIMARY KEY AUTOINCREMENT, "
            for field in fields(UserInfo):
                if field.type is int:
                    create_table_query += f"{field.name} INTEGER"
                else:
                    create_table_query += f"{field.name} TEXT"
                if field is not fields(UserInfo)[-1]:
                    create_table_query += ", "
            create_table_query += ");"
            # print(create_table_query)
            self.cursor.execute(create_table_query)
            self.sql.commit()

    def insert(self, userinfo: UserInfo):
        """
        insert userinfo to table
        """
        insert_query = f"INSERT INTO {self.table} ("
        for field in fields(UserInfo):
            insert_query += f"{field.name}"
            if field is not fields(UserInfo)[-1]:
                insert_query += ", "
        insert_query += ") VALUES ("
        for field in fields(UserInfo):
            insert_query += f"'{getattr(userinfo,field.name)}'"
            if field is not fields(UserInfo)[-1]:
                insert_query += ", "
        insert_query += ");"
        self.cursor.execute(insert_query)
        self.sql.commit()

    def insert_all(self, userinfos: list[UserInfo]):
        """
        insert userinfos to table
        """
        for userinfo in userinfos:
            self.insert(userinfo)

    def print(self):
        """
        print all data in table
        """
        self.cursor.execute(f"SELECT * FROM {self.table}")
        print(self.cursor.fetchall())

    def get_all(self) -> list[UserInfo]:
        """
        get all data in table
        """
        self.cursor.execute(f"SELECT * FROM {self.table}")
        return [UserInfo(*row[1:]) for row in self.cursor.fetchall()]

    def get_by_username(self, username: str) -> UserInfo:
        """
        get data by username
        """
        self.cursor.execute(f"SELECT * FROM {self.table} WHERE username='{username}'")
        result = self.cursor.fetchone()
        if result is None:
            return None
        return UserInfo(*result[1:])

    def delete_table(self):
        """
        delete table
        """
        self.cursor.execute(f"DROP TABLE {self.table}")
        self.sql.commit()


class AdUser:
    def __init__(self, ldap_config: LdapConfig = None, sql: UserSql = None):
        if ldap_config is None:
            ldap_config = LdapConfig()
        if sql is None:
            sql = UserSql()
        self.ldap_config = ldap_config
        self.sql: UserSql = sql
        self.force_gid: int = None
        self.force_gname: str = None
        self.append_groups: list[str] = None
        self.allow_users: list[str] = None

    def user_sync(self):
        ad = MyAD(self.ldap_config)
        ad.connect()
        users = ad.get_user_info_all()
        ad.disconnect()
        self.sql.connect()
        self.sql.delete_table()
        self.sql.create_table()
        self.sql.insert_users_all(users)
        self.sql.disconnect()

    def user_check(self, username: str) -> UserInfo:
        """
        search user in db,if not exist,search in ad and insert into db
        """
        self.sql.connect()
        user = self.sql.get_by_username(username)
        if user is None:
            ad = MyAD(self.ldap_config)
            ad.connect()
            user = ad.get_user_info(username)
            if user is not None:
                self.sql.insert(user)
        self.sql.disconnect()
        if self.force_gid is not None:
            user.gid = self.force_gid
            user.groupname = self.force_gname
        return user