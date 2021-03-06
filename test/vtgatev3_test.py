#!/usr/bin/env python
# coding: utf-8

# Copyright 2019 The Vitess Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from decimal import Decimal
import itertools
import logging
import unittest
import urllib

import environment
import keyspace_util
import utils
from protocols_flavor import protocols_flavor

from vtdb import dbexceptions
from vtdb import vtgate_cursor
from vtdb import vtgate_client


shard_0_master = None
shard_1_master = None
lookup_master = None

keyspace_env = None

create_vt_user = '''create table vt_user (
id bigint,
name varchar(64),
primary key (id)
) Engine=InnoDB'''

create_vt_user2 = '''create table vt_user2 (
id bigint,
name varchar(64),
primary key (id)
) Engine=InnoDB'''

create_vt_user_extra = '''create table vt_user_extra (
user_id bigint,
email varchar(64),
primary key (user_id)
) Engine=InnoDB'''

create_vt_user_extra2 = '''create table vt_user_extra2 (
user_id bigint,
lastname varchar(64),
address varchar(64),
primary key (user_id)
) Engine=InnoDB'''

create_vt_multicolvin = '''create table vt_multicolvin (
kid bigint,
cola varchar(64),
colb varchar(64),
colc varchar(64),
primary key (kid)
) Engine=InnoDB'''

create_vt_aggr = '''create table vt_aggr (
id bigint,
name varchar(64),
primary key (id)
) Engine=InnoDB'''

create_vt_music = '''create table vt_music (
user_id bigint,
id bigint,
song varchar(64),
primary key (user_id, id)
) Engine=InnoDB'''

create_vt_music_extra = '''create table vt_music_extra (
music_id bigint,
user_id bigint,
artist varchar(64),
primary key (music_id)
) Engine=InnoDB'''

create_upsert = '''create table upsert (
pk bigint,
owned bigint,
user_id bigint,
col bigint,
primary key (pk)
) Engine=InnoDB'''

create_join_user = '''create table join_user (
id bigint,
name varchar(64),
primary key (id)
) Engine=InnoDB'''

create_join_user_extra = '''create table join_user_extra (
user_id bigint,
email varchar(64),
primary key (user_id)
) Engine=InnoDB'''

create_join_name_info = '''create table join_name_info (
name varchar(128),
info varchar(128),
primary key (name)
) Engine=InnoDB'''

create_twopc_user = '''create table twopc_user (
user_id bigint,
val varchar(128),
primary key (user_id)
) Engine=InnoDB'''

create_vt_user_seq = '''create table vt_user_seq (
  id int,
  next_id bigint,
  cache bigint,
  primary key(id)
) comment 'vitess_sequence' Engine=InnoDB'''

init_vt_user_seq = 'insert into vt_user_seq values(0, 1, 2)'

create_vt_music_seq = '''create table vt_music_seq (
  id int,
  next_id bigint,
  cache bigint,
  primary key(id)
) comment 'vitess_sequence' Engine=InnoDB'''

init_vt_music_seq = 'insert into vt_music_seq values(0, 1, 2)'

create_vt_main_seq = '''create table vt_main_seq (
  id int,
  next_id bigint,
  cache bigint,
  primary key(id)
) comment 'vitess_sequence' Engine=InnoDB'''

init_vt_main_seq = 'insert into vt_main_seq values(0, 1, 2)'

create_name_user2_map = '''create table name_user2_map (
name varchar(64),
user2_id bigint,
primary key (name, user2_id)
) Engine=InnoDB'''

create_lastname_user_extra2_map = '''create table lastname_user_extra2_map (
lastname varchar(64),
user_id bigint,
primary key (lastname, user_id)
) Engine=InnoDB'''

create_cola_map = '''create table cola_map (
cola varchar(64),
kid binary(8),
primary key (cola, kid)
) Engine=InnoDB'''

create_colb_colc_map = '''create table colb_colc_map (
colb varchar(64),
colc varchar(64),
kid binary(8),
primary key (colb, colc, kid)
) Engine=InnoDB'''

create_address_user_extra2_map = '''create table address_user_extra2_map (
address varchar(64),
user_id bigint,
primary key (address)
) Engine=InnoDB'''

create_music_user_map = '''create table music_user_map (
music_id bigint,
user_id bigint,
primary key (music_id)
) Engine=InnoDB'''

create_upsert_primary = '''create table upsert_primary (
id bigint,
ksnum_id bigint,
primary key (id)
) Engine=InnoDB'''

create_upsert_owned = '''create table upsert_owned (
owned bigint,
ksnum_id bigint,
primary key (owned)
) Engine=InnoDB'''

create_main = '''create table main (
id bigint,
val varchar(128),
primary key(id)
) Engine=InnoDB'''

create_twopc_lookup = '''create table twopc_lookup (
id bigint,
val varchar(128),
primary key (id)
) Engine=InnoDB'''

vschema = {
    'user': '''{
      "sharded": true,
      "vindexes": {
        "hash_index": {
          "type": "hash"
        },
        "unicode_hash": {
          "type": "unicode_loose_md5"
        },
        "name_user2_map": {
          "type": "lookup_hash",
          "params": {
            "table": "name_user2_map",
            "from": "name",
            "to": "user2_id"
          },
          "owner": "vt_user2"
        },
        "lastname_user_extra2_map": {
          "type": "lookup_hash",
          "params": {
            "table": "lastname_user_extra2_map",
            "from": "lastname",
            "to": "user_id"
          },
          "owner": "vt_user_extra2"
        },
        "cola_map": {
          "type": "lookup",
          "params": {
            "table": "cola_map",
            "from": "cola",
            "to": "kid"
          },
          "owner": "vt_multicolvin"
        },
        "colb_colc_map": {
          "type": "lookup",
          "params": {
            "table": "colb_colc_map",
            "from": "colb,colc",
            "to": "kid"
          },
          "owner": "vt_multicolvin"
        },
        "address_user_extra2_map": {
          "type": "lookup_hash_unique",
          "params": {
            "table": "address_user_extra2_map",
            "from": "address",
            "to": "user_id"
          },
          "owner": "vt_user_extra2"
        },
        "music_user_map": {
          "type": "lookup_hash_unique",
          "params": {
            "table": "music_user_map",
            "from": "music_id",
            "to": "user_id"
          },
          "owner": "vt_music"
        },
        "upsert_primary": {
          "type": "lookup_hash_unique",
          "params": {
            "table": "upsert_primary",
            "from": "id",
            "to": "ksnum_id"
          }
        },
        "upsert_owned": {
          "type": "lookup_hash_unique",
          "params": {
            "table": "upsert_owned",
            "from": "owned",
            "to": "ksnum_id"
          },
          "owner": "upsert"
        }
      },
      "tables": {
        "vt_user": {
          "column_vindexes": [
            {
              "column": "id",
              "name": "hash_index"
            }
          ],
          "auto_increment": {
            "column": "id",
            "sequence": "vt_user_seq"
          }
        },
        "vt_user2": {
          "column_vindexes": [
            {
              "column": "id",
              "name": "hash_index"
            },
            {
              "column": "name",
              "name": "name_user2_map"
            }
          ]
        },
        "vt_user_extra": {
          "column_vindexes": [
            {
              "column": "user_id",
              "name": "hash_index"
            }
          ]
        },
        "vt_user_extra2": {
          "column_vindexes": [
            {
              "column": "user_id",
              "name": "hash_index"
            },
            {
              "column": "lastname",
              "name": "lastname_user_extra2_map"
            },
            {
              "column": "address",
              "name": "address_user_extra2_map"
            }
          ]
        },
        "vt_multicolvin": {
          "column_vindexes": [
            {
              "column": "kid",
              "name": "hash_index"
            },
            {
              "column": "cola",
              "name": "cola_map"
            },
            {
              "columns": ["colb", "colc"],
              "name": "colb_colc_map"
            }
          ]
        },
        "vt_aggr": {
          "column_vindexes": [
            {
              "column": "id",
              "name": "hash_index"
            }
          ],
          "columns": [
            {
              "name": "name",
              "type": "VARCHAR"
            }
          ]
        },
        "vt_music": {
          "column_vindexes": [
            {
              "column": "user_id",
              "name": "hash_index"
            },
            {
              "column": "id",
              "name": "music_user_map"
            }
          ],
          "auto_increment": {
            "column": "id",
            "sequence": "vt_music_seq"
          }
        },
        "vt_music_extra": {
          "column_vindexes": [
            {
              "column": "music_id",
              "name": "music_user_map"
            },
            {
              "column": "user_id",
              "name": "hash_index"
            }
          ]
        },
        "upsert": {
          "column_vindexes": [
            {
              "column": "pk",
              "name": "upsert_primary"
            },
            {
              "column": "owned",
              "name": "upsert_owned"
            },
            {
              "column": "user_id",
              "name": "hash_index"
            }
          ]
        },
        "join_user": {
          "column_vindexes": [
            {
              "column": "id",
              "name": "hash_index"
            }
          ]
        },
        "join_user_extra": {
          "column_vindexes": [
            {
              "column": "user_id",
              "name": "hash_index"
            }
          ]
        },
        "join_name_info": {
          "column_vindexes": [
            {
              "column": "name",
              "name": "unicode_hash"
            }
          ]
        },
        "twopc_user": {
          "column_vindexes": [
            {
              "column": "user_id",
              "name": "hash_index"
            }
          ]
        }
      }
    }''',
    'lookup': '''{
      "sharded": false,
      "tables": {
        "vt_user_seq": {
          "type": "sequence"
        },
        "vt_music_seq": {
          "type": "sequence"
        },
        "vt_main_seq": {
          "type": "sequence"
        },
        "music_user_map": {},
        "cola_map": {},
        "colb_colc_map": {},
        "name_user2_map": {},
        "lastname_user_extra2_map": {},
        "address_user_extra2_map": {},
        "upsert_primary": {},
        "upsert_owned": {},
        "main": {
          "auto_increment": {
            "column": "id",
            "sequence": "vt_main_seq"
          }
        },
        "twopc_lookup": {}
      }
    }''',
}


def setUpModule():
  global keyspace_env
  global shard_0_master
  global shard_1_master
  global lookup_master
  logging.debug('in setUpModule')

  try:
    environment.topo_server().setup()
    logging.debug('Setting up tablets')
    keyspace_env = keyspace_util.TestEnv()
    keyspace_env.launch(
        'user',
        shards=['-80', '80-'],
        ddls=[
            create_vt_user,
            create_vt_user2,
            create_vt_user_extra,
            create_vt_user_extra2,
            create_vt_multicolvin,
            create_vt_aggr,
            create_vt_music,
            create_vt_music_extra,
            create_upsert,
            create_join_user,
            create_join_user_extra,
            create_join_name_info,
            create_twopc_user,
            ],
        rdonly_count=1,  # to test SplitQuery
        twopc_coordinator_address='localhost:15028',  # enables 2pc
        )
    keyspace_env.launch(
        'lookup',
        ddls=[
            create_vt_user_seq,
            create_vt_music_seq,
            create_vt_main_seq,
            create_music_user_map,
            create_name_user2_map,
            create_lastname_user_extra2_map,
            create_address_user_extra2_map,
            create_cola_map,
            create_colb_colc_map,
            create_upsert_primary,
            create_upsert_owned,
            create_main,
            create_twopc_lookup,
            ],
        twopc_coordinator_address='localhost:15028',  # enables 2pc
        )
    shard_0_master = keyspace_env.tablet_map['user.-80.master']
    shard_1_master = keyspace_env.tablet_map['user.80-.master']
    lookup_master = keyspace_env.tablet_map['lookup.0.master']

    utils.apply_vschema(vschema)
    utils.VtGate().start(
        tablets=[shard_0_master, shard_1_master, lookup_master],
        extra_args=['-transaction_mode', 'TWOPC'])
    utils.vtgate.wait_for_endpoints('user.-80.master', 1)
    utils.vtgate.wait_for_endpoints('user.80-.master', 1)
    utils.vtgate.wait_for_endpoints('lookup.0.master', 1)
  except:
    tearDownModule()
    raise


def tearDownModule():
  logging.debug('in tearDownModule')
  utils.required_teardown()
  if utils.options.skip_teardown:
    return
  logging.debug('Tearing down the servers and setup')
  if keyspace_env:
    keyspace_env.teardown()

  environment.topo_server().teardown()

  utils.kill_sub_processes()
  utils.remove_tmp_files()


def get_connection(timeout=10.0):
  protocol, endpoint = utils.vtgate.rpc_endpoint(python=True)
  try:
    return vtgate_client.connect(protocol, endpoint, timeout)
  except Exception:
    logging.exception('Connection to vtgate (timeout=%s) failed.', timeout)
    raise


class TestVTGateFunctions(unittest.TestCase):

  decimal_type = 18
  int_type = 265
  string_type = 6165
  varbinary_type = 10262

  def setUp(self):
    self.master_tablet = shard_1_master

  def execute_on_master(self, vtgate_conn, sql, bind_vars):
    return vtgate_conn._execute(
        sql, bind_vars, tablet_type='master', keyspace_name=None)

  def test_health(self):
    f = urllib.urlopen('http://localhost:%d/debug/health' % utils.vtgate.port)
    response = f.read()
    f.close()
    self.assertEqual(response, 'ok')

  def test_srv_vschema(self):
    """Makes sure the SrvVSchema object is properly built."""
    v = utils.run_vtctl_json(['GetSrvVSchema', 'test_nj'])
    self.assertEqual(len(v['keyspaces']), 2, 'wrong vschema: %s' % str(v))
    self.assertIn('user', v['keyspaces'])
    self.assertIn('lookup', v['keyspaces'])

    # Now deletes it.
    utils.run_vtctl(['DeleteSrvVSchema', 'test_nj'])
    _, stderr = utils.run_vtctl(['GetSrvVSchema', 'test_nj'],
                                expect_fail=True)
    self.assertIn('node doesn\'t exist', stderr)

    # And rebuilds it.
    utils.run_vtctl(['RebuildVSchemaGraph', '-cells=test_nj'])
    v = utils.run_vtctl_json(['GetSrvVSchema', 'test_nj'])
    self.assertEqual(len(v['keyspaces']), 2, 'wrong vschema: %s' % str(v))
    self.assertIn('user', v['keyspaces'])
    self.assertIn('lookup', v['keyspaces'])

    # Wait for vtgate to re-read it.
    timeout = 10
    while True:
      vschema_json = utils.vtgate.get_vschema()
      if 'lookup' in vschema_json:
        break
      timeout = utils.wait_step('vtgate re-read vschema', timeout)

  def test_user(self):
    count = 4
    vtgate_conn = get_connection()
    cursor = vtgate_conn.cursor(
        tablet_type='master', keyspace=None, writable=True)

    # Initialize the sequence.
    # TODO(sougou): Use DDL when ready.
    cursor.begin()
    cursor.execute(init_vt_user_seq, {})
    cursor.commit()

    # Test insert
    for x in xrange(count):
      i = x+1
      cursor.begin()
      cursor.execute(
          'insert into vt_user (name) values (:name)',
          {'name': 'test %s' % i})
      self.assertEqual(
          (cursor.fetchall(), cursor.rowcount, cursor.lastrowid,
           cursor.description),
          ([], 1L, i, []))
      cursor.commit()

    # Test select equal
    for x in xrange(count):
      i = x+1
      cursor.execute('select id, name from vt_user where id = :id', {'id': i})
      self.assertEqual(
          (cursor.fetchall(), cursor.rowcount, cursor.lastrowid,
           cursor.description),
          ([(i, 'test %s' % i)], 1L, 0,
           [('id', self.int_type), ('name', self.string_type)]))

    # Test case sensitivity
    cursor.execute('select Id, Name from vt_user where iD = :id', {'id': 1})
    self.assertEqual(
        (cursor.fetchall(), cursor.rowcount, cursor.lastrowid,
         cursor.description),
        ([(1, 'test 1')], 1L, 0,
         [('Id', self.int_type), ('Name', self.string_type)]))

    # test directive timeout
    try:
      cursor.execute('SELECT /*vt+ QUERY_TIMEOUT_MS=10 */ SLEEP(1)', {})
      self.fail('Execute went through')
    except dbexceptions.DatabaseError as e:
      s = str(e)
      self.assertIn(protocols_flavor().rpc_timeout_message(), s)

    # test directive timeout longer than the query time
    cursor.execute('SELECT /*vt+ QUERY_TIMEOUT_MS=2000 */ SLEEP(1)', {})
    self.assertEqual(
        (cursor.fetchall(), cursor.rowcount, cursor.lastrowid,
         cursor.description),
        ([(0,)], 1L, 0,
         [(u'SLEEP(1)', self.int_type)]))

    # test shard errors as warnings directive
    cursor.execute('SELECT /*vt+ SCATTER_ERRORS_AS_WARNINGS */ bad from vt_user', {})
    print vtgate_conn.get_warnings()
    warnings = vtgate_conn.get_warnings()
    self.assertEqual(len(warnings), 2)
    for warning in warnings:
        self.assertEqual(warning.code, 1054)
        self.assertIn('errno 1054', warning.message)
        self.assertIn('Unknown column', warning.message)
    self.assertEqual(
        (cursor.fetchall(), cursor.rowcount, cursor.lastrowid,
         cursor.description),
        ([], 0L, 0, []))

    # test shard errors as warnings directive with timeout
    cursor.execute('SELECT /*vt+ SCATTER_ERRORS_AS_WARNINGS QUERY_TIMEOUT_MS=10 */ SLEEP(1)', {})
    print vtgate_conn.get_warnings()
    warnings = vtgate_conn.get_warnings()
    self.assertEqual(len(warnings), 1)
    for warning in warnings:
        self.assertEqual(warning.code, 1317)
        self.assertIn('context deadline exceeded', warning.message)
    self.assertEqual(
        (cursor.fetchall(), cursor.rowcount, cursor.lastrowid,
         cursor.description),
        ([], 0L, 0, []))

    # Test insert with no auto-inc
    vtgate_conn.begin()
    result = self.execute_on_master(
        vtgate_conn,
        'insert into vt_user (id, name) values (:id, :name)',
        {'id': 6, 'name': 'test 6'})
    self.assertEqual(result, ([], 1L, 0L, []))
    vtgate_conn.commit()

    # Verify values in db
    result = shard_0_master.mquery('vt_user', 'select id, name from vt_user')
    self.assertEqual(result, ((1L, 'test 1'), (2L, 'test 2'), (3L, 'test 3')))
    result = shard_1_master.mquery('vt_user', 'select id, name from vt_user')
    self.assertEqual(result, ((4L, 'test 4'), (6L, 'test 6')))

    # Test MultiValueInsert with no auto-inc
    vtgate_conn.begin()
    result = self.execute_on_master(
        vtgate_conn,
        'insert into vt_user (id, name) values (:id0, :name0), (:id1, :name1)',
        {'id0': 5, 'name0': 'test 5', 'id1': 7, 'name1': 'test 7'})
    self.assertEqual(result, ([], 2L, 0L, []))
    vtgate_conn.commit()

    # Verify values in db
    result = shard_0_master.mquery('vt_user', 'select id, name from vt_user')
    self.assertEqual(result, ((1L, 'test 1'), (2L, 'test 2'), (3L, 'test 3'),
                              (5L, 'test 5')))
    result = shard_1_master.mquery('vt_user', 'select id, name from vt_user')
    self.assertEqual(result, ((4L, 'test 4'), (6L, 'test 6'), (7L, 'test 7')))

    # Test IN clause
    result = self.execute_on_master(
        vtgate_conn,
        'select id, name from vt_user where id in (:a, :b)', {'a': 1, 'b': 4})
    result[0].sort()
    self.assertEqual(
        result,
        ([(1L, 'test 1'), (4L, 'test 4')], 2L, 0,
         [('id', self.int_type), ('name', self.string_type)]))
    result = self.execute_on_master(
        vtgate_conn,
        'select id, name from vt_user where id in (:a, :b)', {'a': 1, 'b': 2})
    result[0].sort()
    self.assertEqual(
        result,
        ([(1L, 'test 1'), (2L, 'test 2')], 2L, 0,
         [('id', self.int_type), ('name', self.string_type)]))

    # Test scatter
    result = vtgate_conn._execute(
        'select id, name from vt_user',
        {}, tablet_type='master', keyspace_name=None)
    result[0].sort()
    self.assertEqual(
        result,
        ([(1L, 'test 1'), (2L, 'test 2'), (3L, 'test 3'), (4L, 'test 4'),
          (5L, 'test 5'), (6L, 'test 6'), (7L, 'test 7')], 7L, 0,
         [('id', self.int_type), ('name', self.string_type)]))

    # Test stream over scatter
    stream_cursor_1 = vtgate_conn.cursor(
        tablet_type='master', keyspace=None,
        cursorclass=vtgate_cursor.StreamVTGateCursor)
    stream_cursor_1.execute('select id, name from vt_user', {})
    stream_cursor_2 = vtgate_conn.cursor(
        tablet_type='master', keyspace=None,
        cursorclass=vtgate_cursor.StreamVTGateCursor)
    stream_cursor_2.execute('select id, name from vt_user', {})
    self.assertEqual(stream_cursor_1.description,
                     [('id', self.int_type), ('name', self.string_type)])
    self.assertEqual(stream_cursor_2.description,
                     [('id', self.int_type), ('name', self.string_type)])
    rows_1 = []
    rows_2 = []
    for row_1, row_2 in itertools.izip(stream_cursor_1, stream_cursor_2):
      rows_1.append(row_1)
      rows_2.append(row_2)
    self.assertEqual(
        sorted(rows_1),
        [(1L, 'test 1'), (2L, 'test 2'), (3L, 'test 3'), (4L, 'test 4'),
         (5L, 'test 5'), (6L, 'test 6'), (7L, 'test 7')])
    self.assertEqual(
        sorted(rows_2),
        [(1L, 'test 1'), (2L, 'test 2'), (3L, 'test 3'), (4L, 'test 4'),
         (5L, 'test 5'), (6L, 'test 6'), (7L, 'test 7')])

    # Test updates
    vtgate_conn.begin()
    result = self.execute_on_master(
        vtgate_conn,
        'update vt_user set name = :name where id = :id',
        {'id': 1, 'name': 'test one'})
    self.assertEqual(result, ([], 1L, 0L, []))
    result = self.execute_on_master(
        vtgate_conn,
        'update vt_user set name = :name where id = :id',
        {'id': 4, 'name': 'test four'})
    self.assertEqual(result, ([], 1L, 0L, []))
    vtgate_conn.commit()
    result = shard_0_master.mquery('vt_user', 'select id, name from vt_user')
    self.assertEqual(
        result, ((1L, 'test one'), (2L, 'test 2'), (3L, 'test 3'),
                 (5L, 'test 5')))
    result = shard_1_master.mquery('vt_user', 'select id, name from vt_user')
    self.assertEqual(
        result, ((4L, 'test four'), (6L, 'test 6'), (7L, 'test 7')))

    # Test deletes
    vtgate_conn.begin()
    result = self.execute_on_master(
        vtgate_conn,
        'delete from vt_user where id = :id',
        {'id': 1})
    self.assertEqual(result, ([], 1L, 0L, []))
    result = self.execute_on_master(
        vtgate_conn,
        'delete from vt_user where id = :id',
        {'id': 4})
    self.assertEqual(result, ([], 1L, 0L, []))
    vtgate_conn.commit()
    result = shard_0_master.mquery('vt_user', 'select id, name from vt_user')
    self.assertEqual(result, ((2L, 'test 2'), (3L, 'test 3'), (5L, 'test 5')))
    result = shard_1_master.mquery('vt_user', 'select id, name from vt_user')
    self.assertEqual(result, ((6L, 'test 6'), (7L, 'test 7')))

    # test passing in the keyspace in the cursor
    lcursor = vtgate_conn.cursor(
        tablet_type='master', keyspace='lookup', writable=True)
    with self.assertRaisesRegexp(
        dbexceptions.DatabaseError, '.*table vt_user not found in schema.*'):
      lcursor.execute('select id, name from vt_user', {})

  def test_user2(self):
    # user2 is for testing non-unique vindexes
    vtgate_conn = get_connection()
    vtgate_conn.begin()
    result = self.execute_on_master(
        vtgate_conn,
        'insert into vt_user2 (id, name) values (:id, :name)',
        {'id': 1, 'name': 'name1'})
    self.assertEqual(result, ([], 1L, 0L, []))
    result = self.execute_on_master(
        vtgate_conn,
        'insert into vt_user2 (id, name) values (:id, :name)',
        {'id': 7, 'name': 'name1'})
    self.assertEqual(result, ([], 1L, 0L, []))
    result = self.execute_on_master(
        vtgate_conn,
        'insert into vt_user2 (id, name) values (:id0, :name0),(:id1, :name1)',
        {'id0': 2, 'name0': 'name2', 'id1': 3, 'name1': 'name2'})
    self.assertEqual(result, ([], 2L, 0L, []))
    vtgate_conn.commit()
    result = shard_0_master.mquery('vt_user', 'select id, name from vt_user2')
    self.assertEqual(result, ((1L, 'name1'), (2L, 'name2'), (3L, 'name2')))
    result = shard_1_master.mquery('vt_user', 'select id, name from vt_user2')
    self.assertEqual(result, ((7L, 'name1'),))
    result = lookup_master.mquery(
        'vt_lookup', 'select name, user2_id from name_user2_map')
    self.assertEqual(result, (('name1', 1L), ('name1', 7L), ('name2', 2L),
                              ('name2', 3L)))

    # Test select by id
    result = self.execute_on_master(
        vtgate_conn,
        'select id, name from vt_user2 where id = :id', {'id': 1})
    self.assertEqual(
        result, ([(1, 'name1')], 1L, 0,
                 [('id', self.int_type), ('name', self.string_type)]))

    # Test select by lookup
    result = self.execute_on_master(
        vtgate_conn,
        'select id, name from vt_user2 where name = :name', {'name': 'name1'})
    result[0].sort()
    self.assertEqual(
        result,
        ([(1, 'name1'), (7, 'name1')], 2L, 0,
         [('id', self.int_type), ('name', self.string_type)]))

    # Test IN clause using non-unique vindex
    result = self.execute_on_master(
        vtgate_conn,
        "select id, name from vt_user2 where name in ('name1', 'name2')", {})
    result[0].sort()
    self.assertEqual(
        result,
        ([(1, 'name1'), (2, 'name2'), (3, 'name2'), (7, 'name1')], 4L, 0,
         [('id', self.int_type), ('name', self.string_type)]))
    result = self.execute_on_master(
        vtgate_conn,
        "select id, name from vt_user2 where name in ('name1')", {})
    result[0].sort()
    self.assertEqual(
        result,
        ([(1, 'name1'), (7, 'name1')], 2L, 0,
         [('id', self.int_type), ('name', self.string_type)]))

    # Test delete
    vtgate_conn.begin()
    result = self.execute_on_master(
        vtgate_conn,
        'delete from vt_user2 where id = :id',
        {'id': 1})
    self.assertEqual(result, ([], 1L, 0L, []))
    result = self.execute_on_master(
        vtgate_conn,
        'delete from vt_user2 where id = :id',
        {'id': 2})
    self.assertEqual(result, ([], 1L, 0L, []))
    vtgate_conn.commit()
    result = shard_0_master.mquery('vt_user', 'select id, name from vt_user2')
    self.assertEqual(result, ((3L, 'name2'),))
    result = shard_1_master.mquery('vt_user', 'select id, name from vt_user2')
    self.assertEqual(result, ((7L, 'name1'),))
    result = lookup_master.mquery(
        'vt_lookup', 'select name, user2_id from name_user2_map')
    self.assertEqual(result, (('name1', 7L), ('name2', 3L)))
    vtgate_conn.begin()
    self.execute_on_master(
        vtgate_conn,
        'delete from vt_user2 where id = :id',
        {'id': 7})
    vtgate_conn.commit()
    vtgate_conn.begin()
    self.execute_on_master(
        vtgate_conn,
        'delete from vt_user2 where id = :id',
        {'id': 3})
    vtgate_conn.commit()

    # Test scatter delete
    vtgate_conn.begin()
    result = self.execute_on_master(
        vtgate_conn,
        'insert into vt_user (id, name) values (:id0, :name0),(:id1, :name1)',
        {'id0': 22, 'name0': 'name2', 'id1': 33, 'name1': 'name2'})
    self.assertEqual(result, ([], 2L, 0L, []))
    result = self.execute_on_master(
        vtgate_conn,
        'delete from vt_user where id > :id',
        {'id': 20})
    self.assertEqual(result, ([], 2L, 0L, []))
    vtgate_conn.commit()

    # Test scatter update
    vtgate_conn.begin()
    result = self.execute_on_master(
        vtgate_conn,
        'insert into vt_user (id, name) values (:id0, :name0),(:id1, :name1)',
        {'id0': 22, 'name0': 'name2', 'id1': 33, 'name1': 'name2'})
    self.assertEqual(result, ([], 2L, 0L, []))
    result = self.execute_on_master(
        vtgate_conn,
        'update vt_user set name=:name where id > :id',
        {'id': 20, 'name': 'jose'})
    self.assertEqual(result, ([], 2L, 0L, []))
    vtgate_conn.commit()

  def test_user_truncate(self):
    vtgate_conn = get_connection()
    vtgate_conn.begin()
    result = self.execute_on_master(
        vtgate_conn,
        'insert into vt_user2 (id, name) values (:id, :name)',
        {'id': 1, 'name': 'name1'})
    self.assertEqual(result, ([], 1L, 0L, []))
    result = self.execute_on_master(
        vtgate_conn,
        'insert into vt_user2 (id, name) values (:id, :name)',
        {'id': 7, 'name': 'name1'})
    self.assertEqual(result, ([], 1L, 0L, []))
    result = self.execute_on_master(
        vtgate_conn,
        'insert into vt_user2 (id, name) values (:id0, :name0),(:id1, :name1)',
        {'id0': 2, 'name0': 'name2', 'id1': 3, 'name1': 'name2'})
    self.assertEqual(result, ([], 2L, 0L, []))
    vtgate_conn.commit()
    result = shard_0_master.mquery('vt_user', 'select id, name from vt_user2')
    self.assertEqual(result, ((1L, 'name1'), (2L, 'name2'), (3L, 'name2')))
    result = shard_1_master.mquery('vt_user', 'select id, name from vt_user2')
    self.assertEqual(result, ((7L, 'name1'),))
    result = lookup_master.mquery(
        'vt_lookup', 'select name, user2_id from name_user2_map')
    self.assertEqual(result, (('name1', 1L), ('name1', 7L), ('name2', 2L),
                              ('name2', 3L)))
    vtgate_conn.begin()
    result = vtgate_conn._execute(
        'truncate vt_user2',
        {},
        tablet_type='master',
        keyspace_name='user'
    )
    vtgate_conn.commit()
    lookup_master.mquery('vt_lookup', 'truncate name_user2_map')
    self.assertEqual(result, ([], 0L, 0L, []))
    # Test select by id
    result = self.execute_on_master(
        vtgate_conn,
        'select id, name from vt_user2 where id = :id', {'id': 1})
    self.assertEqual(
        result, ([], 0L, 0, [('id', self.int_type),
                             ('name', self.string_type)]))

  def test_user_extra(self):
    # user_extra is for testing unowned functional vindex
    count = 4
    vtgate_conn = get_connection()
    for x in xrange(count):
      i = x+1
      vtgate_conn.begin()
      result = self.execute_on_master(
          vtgate_conn,
          'insert into vt_user_extra (user_id, email) '
          'values (:user_id, :email)',
          {'user_id': i, 'email': 'test %s' % i})
      self.assertEqual(result, ([], 1L, 0L, []))
      vtgate_conn.commit()
    for x in xrange(count):
      i = x+1
      result = self.execute_on_master(
          vtgate_conn,
          'select user_id, email from vt_user_extra where user_id = :user_id',
          {'user_id': i})
      self.assertEqual(
          result,
          ([(i, 'test %s' % i)], 1L, 0,
           [('user_id', self.int_type), ('email', self.string_type)]))
    result = shard_0_master.mquery(
        'vt_user', 'select user_id, email from vt_user_extra')
    self.assertEqual(result, ((1L, 'test 1'), (2L, 'test 2'), (3L, 'test 3')))
    result = shard_1_master.mquery(
        'vt_user', 'select user_id, email from vt_user_extra')
    self.assertEqual(result, ((4L, 'test 4'),))

    vtgate_conn.begin()
    result = self.execute_on_master(
        vtgate_conn,
        'update vt_user_extra set email = :email where user_id = :user_id',
        {'user_id': 1, 'email': 'test one'})
    self.assertEqual(result, ([], 1L, 0L, []))
    result = self.execute_on_master(
        vtgate_conn,
        'update vt_user_extra set email = :email where user_id = :user_id',
        {'user_id': 4, 'email': 'test four'})
    self.assertEqual(result, ([], 1L, 0L, []))
    vtgate_conn.commit()
    result = shard_0_master.mquery(
        'vt_user', 'select user_id, email from vt_user_extra')
    self.assertEqual(result, ((1L, 'test one'), (2L, 'test 2'), (3L, 'test 3')))
    result = shard_1_master.mquery(
        'vt_user', 'select user_id, email from vt_user_extra')
    self.assertEqual(result, ((4L, 'test four'),))

    vtgate_conn.begin()
    result = self.execute_on_master(
        vtgate_conn,
        'delete from vt_user_extra where user_id = :user_id',
        {'user_id': 1})
    self.assertEqual(result, ([], 1L, 0L, []))
    result = self.execute_on_master(
        vtgate_conn,
        'delete from  vt_user_extra where user_id = :user_id',
        {'user_id': 4})
    self.assertEqual(result, ([], 1L, 0L, []))
    vtgate_conn.commit()
    result = shard_0_master.mquery(
        'vt_user', 'select user_id, email from vt_user_extra')
    self.assertEqual(result, ((2L, 'test 2'), (3L, 'test 3')))
    result = shard_1_master.mquery(
        'vt_user', 'select user_id, email from vt_user_extra')
    self.assertEqual(result, ())
    vtgate_conn.begin()
    self.execute_on_master(
        vtgate_conn,
        'delete from  vt_user_extra where user_id = :user_id',
        {'user_id': 2})
    self.execute_on_master(
        vtgate_conn,
        'delete from  vt_user_extra where user_id = :user_id',
        {'user_id': 3})
    vtgate_conn.commit()

  def test_user_scatter_limit(self):
    vtgate_conn = get_connection()
    # Works when there is no data
    result = self.execute_on_master(
        vtgate_conn,
        'select id from vt_user2 order by id limit :limit offset :offset ', {'limit': 4, 'offset': 1})
    self.assertEqual(
        result, ([], 0L, 0, [('id', self.int_type)]))

    vtgate_conn.begin()
    result = self.execute_on_master(
        vtgate_conn,
        'insert into vt_user2 (id, name) values (:id0, :name0),(:id1, :name1),(:id2, :name2), (:id3, :name3), (:id4, :name4)',
        {
          'id0': 1, 'name0': 'name0',
          'id1': 2, 'name1': 'name1',
          'id2': 3, 'name2': 'name2',
          'id3': 4, 'name3': 'name3',
          'id4': 5, 'name4': 'name4',
        }
    )
    self.assertEqual(result, ([], 5L, 0L, []))
    vtgate_conn.commit()
    # Assert that rows are in multiple shards
    result = shard_0_master.mquery('vt_user', 'select id, name from vt_user2')
    self.assertEqual(result, ((1L, 'name0'), (2L, 'name1'), (3L, 'name2'), (5L, 'name4')))
    result = shard_1_master.mquery('vt_user', 'select id, name from vt_user2')
    self.assertEqual(result, ((4L, 'name3'),))

    # Works when limit is set
    result = self.execute_on_master(
      vtgate_conn,
      'select id from vt_user2 order by id limit :limit', {'limit': 2 })
    self.assertEqual(
        result,
        ([(1,),(2,),], 2L, 0,
         [('id', self.int_type)]))


    # Fetching with offset works
    count = 4
    for x in xrange(count):
      i = x+1
      result = self.execute_on_master(
        vtgate_conn,
        'select id from vt_user2 order by id limit :limit offset :offset ', {'limit': 1, 'offset': x})
      self.assertEqual(
        result,
        ([(i,)], 1L, 0,
         [('id', self.int_type)]))

    # Works when limit is greater than values in the table
    result = self.execute_on_master(
      vtgate_conn,
      'select id from vt_user2 order by id limit :limit offset :offset ', {'limit': 100, 'offset': 1})
    self.assertEqual(
        result,
        ([(2,),(3,),(4,),(5,)], 4L, 0,
         [('id', self.int_type)]))

    # Works without bind vars
    result = self.execute_on_master(
      vtgate_conn,
      'select id from vt_user2 order by id limit 1 offset 1', {})
    self.assertEqual(
        result,
        ([(2,)], 1L, 0,
         [('id', self.int_type)]))

    vtgate_conn.begin()
    result = vtgate_conn._execute(
        'truncate vt_user2',
        {},
        tablet_type='master',
        keyspace_name='user'
    )
    vtgate_conn.commit()
    lookup_master.mquery('vt_lookup', 'truncate name_user2_map')

  def test_user_extra2(self):
    # user_extra2 is for testing updates to secondary vindexes
    vtgate_conn = get_connection()
    vtgate_conn.begin()
    result = self.execute_on_master(
        vtgate_conn,
        'insert into vt_user_extra2 (user_id, lastname, address) '
        'values (:user_id, :lastname, :address)',
        {'user_id': 5, 'lastname': 'nieves', 'address': 'invernalia'})
    self.assertEqual(result, ([], 1L, 0L, []))
    vtgate_conn.commit()

    # Updating both vindexes
    vtgate_conn.begin()
    result = self.execute_on_master(
        vtgate_conn,
        'update vt_user_extra2 set lastname = :lastname,'
        ' address = :address where user_id = :user_id',
        {'user_id': 5, 'lastname': 'buendia', 'address': 'macondo'})
    self.assertEqual(result, ([], 1L, 0L, []))
    vtgate_conn.commit()
    result = self.execute_on_master(
        vtgate_conn,
        'select lastname, address from vt_user_extra2 where user_id = 5', {})
    self.assertEqual(
        result,
        ([('buendia', 'macondo')], 1, 0,
         [('lastname', self.string_type),
          ('address', self.string_type)]))
    result = lookup_master.mquery(
        'vt_lookup', 'select lastname, user_id from lastname_user_extra2_map')
    self.assertEqual(
        result,
        (('buendia', 5L),))
    result = lookup_master.mquery(
        'vt_lookup', 'select address, user_id from address_user_extra2_map')
    self.assertEqual(
        result,
        (('macondo', 5L),))

    # Updating only one vindex
    vtgate_conn.begin()
    result = self.execute_on_master(
        vtgate_conn,
        'update vt_user_extra2 set address = :address where user_id = :user_id',
        {'user_id': 5, 'address': 'yoknapatawpha'})
    self.assertEqual(result, ([], 1L, 0L, []))
    vtgate_conn.commit()
    result = self.execute_on_master(
        vtgate_conn,
        'select lastname, address from vt_user_extra2 where user_id = 5', {})
    self.assertEqual(
        result,
        ([('buendia', 'yoknapatawpha')], 1, 0,
         [('lastname', self.string_type),
          ('address', self.string_type)]))
    result = lookup_master.mquery(
        'vt_lookup', 'select address, user_id from address_user_extra2_map')
    self.assertEqual(
        result,
        (('yoknapatawpha', 5L),))
    result = lookup_master.mquery(
        'vt_lookup', 'select lastname, user_id from lastname_user_extra2_map')
    self.assertEqual(
        result,
        (('buendia', 5L),))

    # It works when you update to same value on unique index
    vtgate_conn.begin()
    result = self.execute_on_master(
        vtgate_conn,
        'update vt_user_extra2 set address = :address where user_id = :user_id',
        {'user_id': 5, 'address': 'yoknapatawpha'})
    self.assertEqual(result, ([], 0L, 0L, []))
    vtgate_conn.commit()
    result = self.execute_on_master(
        vtgate_conn,
        'select lastname, address from vt_user_extra2 where user_id = 5', {})
    self.assertEqual(
        result,
        ([('buendia', 'yoknapatawpha')], 1, 0,
         [('lastname', self.string_type),
          ('address', self.string_type)]))
    result = lookup_master.mquery(
        'vt_lookup', 'select lastname, user_id from lastname_user_extra2_map')
    self.assertEqual(
        result,
        (('buendia', 5L),))
    result = lookup_master.mquery(
        'vt_lookup', 'select address, user_id from address_user_extra2_map')
    self.assertEqual(
        result,
        (('yoknapatawpha', 5L),))

    # you can find the record by either vindex
    result = self.execute_on_master(
        vtgate_conn,
        'select lastname, address from vt_user_extra2'
        ' where lastname = "buendia"', {})
    self.assertEqual(
        result,
        ([('buendia', 'yoknapatawpha')], 1, 0,
         [('lastname', self.string_type),
          ('address', self.string_type)]))
    result = self.execute_on_master(
        vtgate_conn,
        'select lastname, address from vt_user_extra2'
        ' where address = "yoknapatawpha"', {})
    self.assertEqual(
        result,
        ([('buendia', 'yoknapatawpha')], 1, 0,
         [('lastname', self.string_type),
          ('address', self.string_type)]))

  def test_multicolvin(self):
    # multicolvin tests a table with a multi column vindex
    vtgate_conn = get_connection()
    vtgate_conn.begin()
    result = self.execute_on_master(
        vtgate_conn,
        'insert into vt_multicolvin (cola, colb, colc, kid) '
        'values (:cola, :colb, :colc, :kid)',
        {'kid': 5, 'cola': 'cola_value', 'colb': 'colb_value',
         'colc': 'colc_value'})
    self.assertEqual(result, ([], 1L, 0L, []))
    vtgate_conn.commit()

    # Updating both vindexes
    vtgate_conn.begin()
    result = self.execute_on_master(
        vtgate_conn,
        'update vt_multicolvin set cola = :cola, colb = :colb, colc = :colc'
        ' where kid = :kid',
        {'kid': 5, 'cola': 'cola_newvalue', 'colb': 'colb_newvalue',
         'colc': 'colc_newvalue'})
    self.assertEqual(result, ([], 1L, 0L, []))
    vtgate_conn.commit()
    result = self.execute_on_master(
        vtgate_conn,
        'select cola, colb, colc from vt_multicolvin where kid = 5', {})
    self.assertEqual(
        result,
        ([('cola_newvalue', 'colb_newvalue', 'colc_newvalue')], 1, 0,
         [('cola', self.string_type),
          ('colb', self.string_type),
          ('colc', self.string_type)]))
    result = lookup_master.mquery(
        'vt_lookup', 'select cola from cola_map')
    self.assertEqual(
        result,
        (('cola_newvalue',),))
    result = lookup_master.mquery(
        'vt_lookup', 'select colb, colc from colb_colc_map')
    self.assertEqual(
        result,
        (('colb_newvalue', 'colc_newvalue'),))

    # Updating only one vindex
    vtgate_conn.begin()
    result = self.execute_on_master(
        vtgate_conn,
        'update vt_multicolvin set colb = :colb, colc = :colc where kid = :kid',
        {'kid': 5, 'colb': 'colb_newvalue2', 'colc': 'colc_newvalue2'})
    self.assertEqual(result, ([], 1L, 0L, []))
    vtgate_conn.commit()
    result = self.execute_on_master(
        vtgate_conn, 'select colb, colc from vt_multicolvin where kid = 5', {})
    self.assertEqual(
        result,
        ([('colb_newvalue2', 'colc_newvalue2')], 1, 0,
         [('colb', self.string_type),
          ('colc', self.string_type)]))
    result = lookup_master.mquery(
        'vt_lookup', 'select colb, colc from colb_colc_map')
    self.assertEqual(
        result,
        (('colb_newvalue2', 'colc_newvalue2'),))

    # Works when inserting multiple rows
    vtgate_conn = get_connection()
    vtgate_conn.begin()
    result = self.execute_on_master(
        vtgate_conn,
        'insert into vt_multicolvin (cola, colb, colc, kid) '
        'values (:cola0, :colb0, :colc0, :kid0),'
        ' (:cola1, :colb1, :colc1, :kid1)',
        {'kid0': 6, 'cola0': 'cola0_value', 'colb0': 'colb0_value',
         'colc0': 'colc0_value',
         'kid1': 7, 'cola1': 'cola1_value', 'colb1': 'colb1_value',
         'colc1': 'colc1_value'
        })
    self.assertEqual(result, ([], 2L, 0L, []))
    vtgate_conn.commit()

  def test_aggr(self):
    # test_aggr tests text column aggregation
    vtgate_conn = get_connection()
    vtgate_conn.begin()
    # insert upper and lower-case mixed rows in jumbled order
    result = self.execute_on_master(
        vtgate_conn,
        'insert into vt_aggr (id, name) values '
        '(10, \'A\'), '
        '(9, \'a\'), '
        '(8, \'b\'), '
        '(7, \'B\'), '
        '(6, \'d\'), '
        '(5, \'c\'), '
        '(4, \'C\'), '
        '(3, \'d\'), '
        '(2, \'e\'), '
        '(1, \'E\')',
        {})
    vtgate_conn.commit()

    result = self.execute_on_master(
        vtgate_conn, 'select sum(id), name from vt_aggr group by name', {})
    values = [v1 for v1, v2 in result[0]]
    print values
    self.assertEqual(
        [v1 for v1, v2 in result[0]],
        [(Decimal('19')),
          (Decimal('15')),
          (Decimal('9')),
          (Decimal('9')),
          (Decimal('3'))])

  def test_music(self):
    # music is for testing owned lookup index
    vtgate_conn = get_connection()

    # Initialize the sequence.
    # TODO(sougou): Use DDL when ready.
    vtgate_conn.begin()
    self.execute_on_master(vtgate_conn, init_vt_music_seq, {})
    vtgate_conn.commit()

    count = 4
    for x in xrange(count):
      i = x+1
      vtgate_conn.begin()
      result = self.execute_on_master(
          vtgate_conn,
          'insert into vt_music (user_id, song) values (:user_id, :song)',
          {'user_id': i, 'song': 'test %s' % i})
      self.assertEqual(result, ([], 1L, i, []))
      vtgate_conn.commit()
    for x in xrange(count):
      i = x+1
      result = self.execute_on_master(
          vtgate_conn,
          'select user_id, id, song from vt_music where id = :id', {'id': i})
      self.assertEqual(
          result,
          ([(i, i, 'test %s' % i)], 1, 0,
           [('user_id', self.int_type),
            ('id', self.int_type),
            ('song', self.string_type)]))
    vtgate_conn.begin()
    result = self.execute_on_master(
        vtgate_conn,
        'insert into vt_music (user_id, id, song) '
        'values (:user_id0, :id0, :song0), (:user_id1, :id1, :song1)',
        {'user_id0': 5, 'id0': 6, 'song0': 'test 6', 'user_id1': 7, 'id1': 7,
         'song1': 'test 7'})
    self.assertEqual(result, ([], 2L, 0L, []))
    vtgate_conn.commit()
    result = shard_0_master.mquery(
        'vt_user', 'select user_id, id, song from vt_music')
    self.assertEqual(
        result,
        ((1L, 1L, 'test 1'), (2L, 2L, 'test 2'), (3L, 3L, 'test 3'),
         (5L, 6L, 'test 6')))
    result = shard_1_master.mquery(
        'vt_user', 'select user_id, id, song from vt_music')
    self.assertEqual(
        result, ((4L, 4L, 'test 4'), (7L, 7L, 'test 7')))
    result = lookup_master.mquery(
        'vt_lookup', 'select music_id, user_id from music_user_map')
    self.assertEqual(
        result,
        ((1L, 1L), (2L, 2L), (3L, 3L), (4L, 4L), (6L, 5L), (7L, 7L)))

    vtgate_conn.begin()
    result = self.execute_on_master(
        vtgate_conn,
        'update vt_music set song = :song where id = :id',
        {'id': 6, 'song': 'test six'})
    self.assertEqual(result, ([], 1L, 0L, []))
    result = self.execute_on_master(
        vtgate_conn,
        'update vt_music set song = :song where id = :id',
        {'id': 4, 'song': 'test four'})
    self.assertEqual(result, ([], 1L, 0L, []))
    vtgate_conn.commit()
    result = shard_0_master.mquery(
        'vt_user', 'select user_id, id, song from vt_music')
    self.assertEqual(
        result, ((1L, 1L, 'test 1'), (2L, 2L, 'test 2'), (3L, 3L, 'test 3'),
                 (5L, 6L, 'test six')))
    result = shard_1_master.mquery(
        'vt_user', 'select user_id, id, song from vt_music')
    self.assertEqual(
        result, ((4L, 4L, 'test four'), (7L, 7L, 'test 7')))

    vtgate_conn.begin()
    result = self.execute_on_master(
        vtgate_conn,
        'delete from vt_music where id = :id',
        {'id': 3})
    self.assertEqual(result, ([], 1L, 0L, []))
    result = self.execute_on_master(
        vtgate_conn,
        'delete from vt_music where user_id = :user_id',
        {'user_id': 4})
    self.assertEqual(result, ([], 1L, 0L, []))
    vtgate_conn.commit()
    result = shard_0_master.mquery(
        'vt_user', 'select user_id, id, song from vt_music')
    self.assertEqual(
        result, ((1L, 1L, 'test 1'), (2L, 2L, 'test 2'), (5L, 6L, 'test six')))
    result = shard_1_master.mquery(
        'vt_user', 'select user_id, id, song from vt_music')
    self.assertEqual(result, ((7L, 7L, 'test 7'),))
    result = lookup_master.mquery(
        'vt_lookup', 'select music_id, user_id from music_user_map')
    self.assertEqual(result, ((1L, 1L), (2L, 2L), (6L, 5L), (7L, 7L)))

  def test_music_extra(self):
    # music_extra is for testing unonwed lookup index
    vtgate_conn = get_connection()
    vtgate_conn.begin()
    result = self.execute_on_master(
        vtgate_conn,
        'insert into vt_music_extra (music_id, user_id, artist) '
        'values (:music_id, :user_id, :artist)',
        {'music_id': 1, 'user_id': 1, 'artist': 'test 1'})
    self.assertEqual(result, ([], 1L, 0L, []))
    result = self.execute_on_master(
        vtgate_conn,
        'insert into vt_music_extra (music_id, artist) '
        'values (:music_id0, :artist0), (:music_id1, :artist1)',
        {'music_id0': 6, 'artist0': 'test 6', 'music_id1': 7,
         'artist1': 'test 7'})
    self.assertEqual(result, ([], 2L, 0L, []))
    vtgate_conn.commit()
    result = self.execute_on_master(
        vtgate_conn,
        'select music_id, user_id, artist '
        'from vt_music_extra where music_id = :music_id',
        {'music_id': 6})
    self.assertEqual(
        result, ([(6L, 5L, 'test 6')], 1, 0,
                 [('music_id', self.int_type),
                  ('user_id', self.int_type),
                  ('artist', self.string_type)]))
    result = shard_0_master.mquery(
        'vt_user', 'select music_id, user_id, artist from vt_music_extra')
    self.assertEqual(result, ((1L, 1L, 'test 1'), (6L, 5L, 'test 6')))
    result = shard_1_master.mquery(
        'vt_user', 'select music_id, user_id, artist from vt_music_extra')
    self.assertEqual(result, ((7L, 7L, 'test 7'),))

    vtgate_conn.begin()
    result = self.execute_on_master(
        vtgate_conn,
        'update vt_music_extra set artist = :artist '
        'where music_id = :music_id',
        {'music_id': 6, 'artist': 'test six'})
    self.assertEqual(result, ([], 1L, 0L, []))
    result = self.execute_on_master(
        vtgate_conn,
        'update vt_music_extra set artist = :artist '
        'where music_id = :music_id',
        {'music_id': 7, 'artist': 'test seven'})
    self.assertEqual(result, ([], 1L, 0L, []))
    vtgate_conn.commit()
    result = shard_0_master.mquery(
        'vt_user', 'select music_id, user_id, artist from vt_music_extra')
    self.assertEqual(result, ((1L, 1L, 'test 1'), (6L, 5L, 'test six')))
    result = shard_1_master.mquery(
        'vt_user', 'select music_id, user_id, artist from vt_music_extra')
    self.assertEqual(result, ((7L, 7L, 'test seven'),))

    vtgate_conn.begin()
    result = self.execute_on_master(
        vtgate_conn,
        'delete from vt_music_extra where music_id = :music_id',
        {'music_id': 6})
    self.assertEqual(result, ([], 1L, 0L, []))
    result = self.execute_on_master(
        vtgate_conn,
        'delete from vt_music_extra where music_id = :music_id',
        {'music_id': 7})
    self.assertEqual(result, ([], 1L, 0L, []))
    vtgate_conn.commit()
    result = shard_0_master.mquery(
        'vt_user', 'select music_id, user_id, artist from vt_music_extra')
    self.assertEqual(result, ((1L, 1L, 'test 1'),))
    result = shard_1_master.mquery(
        'vt_user', 'select music_id, user_id, artist from vt_music_extra')
    self.assertEqual(result, ())

  def test_main_seq(self):
    vtgate_conn = get_connection()

    # Initialize the sequence.
    # TODO(sougou): Use DDL when ready.
    vtgate_conn.begin()
    self.execute_on_master(vtgate_conn, init_vt_main_seq, {})
    vtgate_conn.commit()

    count = 4
    for x in xrange(count):
      i = x+1
      vtgate_conn.begin()
      result = self.execute_on_master(
          vtgate_conn,
          'insert into main (val) values (:val)',
          {'val': 'test %s' % i})
      self.assertEqual(result, ([], 1L, i, []))
      vtgate_conn.commit()

    result = self.execute_on_master(
        vtgate_conn, 'select id, val from main where id = 4', {})
    self.assertEqual(
        result,
        ([(4, 'test 4')], 1, 0,
         [('id', self.int_type),
          ('val', self.string_type)]))

    # Now test direct calls to sequence.
    result = self.execute_on_master(
        vtgate_conn, 'select next 1 values from vt_main_seq', {})
    self.assertEqual(
        result,
        ([(5,)], 1, 0,
         [('nextval', self.int_type)]))

  def test_upsert(self):
    vtgate_conn = get_connection()

    # Create lookup entries for primary vindex:
    # No entry for 2. upsert_primary is not owned.
    # So, we need to pre-create entries that the
    # subsequent will insert will use to compute the
    # keyspace id.
    vtgate_conn.begin()
    self.execute_on_master(
        vtgate_conn,
        'insert into upsert_primary(id, ksnum_id) values'
        '(1, 1), (3, 3), (4, 4), (5, 5), (6, 6)',
        {})
    vtgate_conn.commit()

    # Create rows on the main table.
    vtgate_conn.begin()
    self.execute_on_master(
        vtgate_conn,
        'insert into upsert(pk, owned, user_id, col) values'
        '(1, 1, 1, 0), (3, 3, 3, 0), (4, 4, 4, 0), (5, 5, 5, 0), (6, 6, 6, 0)',
        {})
    vtgate_conn.commit()

    # Now upsert: 1, 5 and 6 should succeed.
    vtgate_conn.begin()
    self.execute_on_master(
        vtgate_conn,
        'insert into upsert(pk, owned, user_id, col) values'
        '(1, 1, 1, 1), (2, 2, 2, 2), (3, 1, 1, 3), (4, 4, 1, 4), '
        '(5, 5, 5, 5), (6, 6, 6, 6) '
        'on duplicate key update col = values(col)',
        {})
    vtgate_conn.commit()

    result = self.execute_on_master(
        vtgate_conn,
        'select pk, owned, user_id, col from upsert order by pk',
        {})
    self.assertEqual(
        result[0],
        [(1, 1, 1, 1), (3, 3, 3, 0), (4, 4, 4, 0),
         (5, 5, 5, 5), (6, 6, 6, 6)])

    # insert ignore
    vtgate_conn.begin()
    self.execute_on_master(
        vtgate_conn,
        'insert into upsert_primary(id, ksnum_id) values(7, 7)',
        {})
    vtgate_conn.commit()
    # 1 will be sent but will not change existing row.
    # 2 will not be sent because there is no keyspace id for it.
    # 7 will be sent and will create a row.
    vtgate_conn.begin()
    self.execute_on_master(
        vtgate_conn,
        'insert ignore into upsert(pk, owned, user_id, col) values'
        '(1, 1, 1, 2), (2, 2, 2, 2), (7, 7, 7, 7)',
        {})
    vtgate_conn.commit()

    result = self.execute_on_master(
        vtgate_conn,
        'select pk, owned, user_id, col from upsert order by pk',
        {})
    self.assertEqual(
        result[0],
        [(1, 1, 1, 1), (3, 3, 3, 0), (4, 4, 4, 0),
         (5, 5, 5, 5), (6, 6, 6, 6), (7, 7, 7, 7)])

  def test_joins_subqueries(self):
    vtgate_conn = get_connection()
    vtgate_conn.begin()
    self.execute_on_master(
        vtgate_conn,
        'insert into join_user (id, name) values (:id, :name)',
        {'id': 1, 'name': 'name1'})
    self.execute_on_master(
        vtgate_conn,
        'insert into join_user_extra (user_id, email) '
        'values (:user_id, :email)',
        {'user_id': 1, 'email': 'email1'})
    self.execute_on_master(
        vtgate_conn,
        'insert into join_user_extra (user_id, email) '
        'values (:user_id, :email)',
        {'user_id': 2, 'email': 'email2'})
    self.execute_on_master(
        vtgate_conn,
        'insert into join_name_info (name, info) '
        'values (:name, :info)',
        {'name': 'name1', 'info': 'name test'})
    vtgate_conn.commit()
    result = self.execute_on_master(
        vtgate_conn,
        'select u.id, u.name, e.user_id, e.email '
        'from join_user u join join_user_extra e where e.user_id = u.id',
        {})
    self.assertEqual(
        result,
        ([(1L, 'name1', 1L, 'email1')],
         1,
         0,
         [('id', self.int_type),
          ('name', self.string_type),
          ('user_id', self.int_type),
          ('email', self.string_type)]))
    result = self.execute_on_master(
        vtgate_conn,
        'select u.id, u.name, e.user_id, e.email '
        'from join_user u join join_user_extra e where e.user_id = u.id+1',
        {})
    self.assertEqual(
        result,
        ([(1L, 'name1', 2L, 'email2')],
         1,
         0,
         [('id', self.int_type),
          ('name', self.string_type),
          ('user_id', self.int_type),
          ('email', self.string_type)]))
    result = self.execute_on_master(
        vtgate_conn,
        'select u.id, u.name, e.user_id, e.email '
        'from join_user u left join join_user_extra e on e.user_id = u.id+1',
        {})
    self.assertEqual(
        result,
        ([(1L, 'name1', 2L, 'email2')],
         1,
         0,
         [('id', self.int_type),
          ('name', self.string_type),
          ('user_id', self.int_type),
          ('email', self.string_type)]))
    result = self.execute_on_master(
        vtgate_conn,
        'select u.id, u.name, e.user_id, e.email '
        'from join_user u left join join_user_extra e on e.user_id = u.id+2',
        {})
    self.assertEqual(
        result,
        ([(1L, 'name1', None, None)],
         1,
         0,
         [('id', self.int_type),
          ('name', self.string_type),
          ('user_id', self.int_type),
          ('email', self.string_type)]))
    result = self.execute_on_master(
        vtgate_conn,
        'select u.id, u.name, e.user_id, e.email '
        'from join_user u join join_user_extra e on e.user_id = u.id+2 '
        'where u.id = 2',
        {})
    self.assertEqual(
        result,
        ([],
         0,
         0,
         [('id', self.int_type),
          ('name', self.string_type),
          ('user_id', self.int_type),
          ('email', self.string_type)]))
    result = self.execute_on_master(
        vtgate_conn,
        'select u.id, u.name, n.info '
        'from join_user u join join_name_info n on u.name = n.name '
        'where u.id = 1',
        {})
    self.assertEqual(
        result,
        ([(1L, 'name1', 'name test')],
         1,
         0,
         [('id', self.int_type),
          ('name', self.string_type),
          ('info', self.string_type)]))

    # test a cross-shard subquery
    result = self.execute_on_master(
        vtgate_conn,
        'select id, name from join_user '
        'where id in (select user_id from join_user_extra)',
        {})
    self.assertEqual(
        result,
        ([(1L, 'name1')],
         1,
         0,
         [('id', self.int_type),
          ('name', self.string_type)]))
    vtgate_conn.begin()
    self.execute_on_master(
        vtgate_conn,
        'delete from join_user where id = :id',
        {'id': 1})
    self.execute_on_master(
        vtgate_conn,
        'delete from  join_user_extra where user_id = :user_id',
        {'user_id': 1})
    self.execute_on_master(
        vtgate_conn,
        'delete from  join_user_extra where user_id = :user_id',
        {'user_id': 2})
    vtgate_conn.commit()

  def test_insert_value_required(self):
    vtgate_conn = get_connection()
    try:
      vtgate_conn.begin()
      with self.assertRaisesRegexp(dbexceptions.DatabaseError,
                                   '.*could not map NULL to a keyspace id.*'):
        self.execute_on_master(
            vtgate_conn,
            'insert into vt_user_extra (email) values (:email)',
            {'email': 'test 10'})
    finally:
      vtgate_conn.rollback()

  def test_vindex_func(self):
    vtgate_conn = get_connection()
    result = self.execute_on_master(
        vtgate_conn,
        'select id, keyspace_id from hash_index where id = :id',
        {'id': 1})
    self.assertEqual(
        result,
        ([('1', '\x16k@\xb4J\xbaK\xd6')],
         1,
         0,
         [('id', self.varbinary_type),
          ('keyspace_id', self.varbinary_type)]))

  def test_analyze_table(self):
    vtgate_conn = get_connection()
    self.execute_on_master(
        vtgate_conn,
        'use user',
        {})
    result = self.execute_on_master(
        vtgate_conn,
        'analyze table vt_user',
        {})
    self.assertEqual(
        result[0],
        [('vt_user.vt_user', 'analyze', 'status', 'OK')])

  def test_transaction_modes(self):
    vtgate_conn = get_connection()
    cursor = vtgate_conn.cursor(
        tablet_type='master', keyspace=None, writable=True, single_db=True)
    cursor.begin()
    cursor.execute(
        'insert into twopc_user (user_id, val)  values(1, \'val\')', {})
    with self.assertRaisesRegexp(
        dbexceptions.DatabaseError, '.*multi-db transaction attempted.*'):
      cursor.execute(
          'insert into twopc_lookup (id, val)  values(1, \'val\')', {})

    cursor = vtgate_conn.cursor(
        tablet_type='master', keyspace=None, writable=True, twopc=True)
    cursor.begin()
    cursor.execute(
        'insert into twopc_user (user_id, val)  values(1, \'val\')', {})
    cursor.execute(
        'insert into twopc_lookup (id, val)  values(1, \'val\')', {})
    cursor.commit()

    cursor.execute('select user_id, val from twopc_user where user_id = 1', {})
    self.assertEqual(cursor.fetchall(), [(1, 'val')])
    cursor.execute('select id, val from twopc_lookup where id = 1', {})
    self.assertEqual(cursor.fetchall(), [(1, 'val')])

    cursor.begin()
    cursor.execute('delete from twopc_user where user_id = 1', {})
    cursor.execute('delete from twopc_lookup where id = 1', {})
    cursor.commit()

    cursor.execute('select user_id, val from twopc_user where user_id = 1', {})
    self.assertEqual(cursor.fetchall(), [])
    cursor.execute('select id, val from twopc_lookup where id = 1', {})
    self.assertEqual(cursor.fetchall(), [])

  def test_vtclient(self):
    """This test uses vtclient to send and receive various queries.
    """
    # specify a good default keyspace for the connection here.
    utils.vtgate.vtclient(
        'insert into vt_user_extra(user_id, email) values (:v1, :v2)',
        keyspace='user',
        bindvars=[10, 'test 10'])

    out, _ = utils.vtgate.vtclient(
        'select user_id, email from vt_user_extra where user_id = :v1',
        bindvars=[10], json_output=True)
    self.assertEqual(out, {
        u'fields': [u'user_id', u'email'],
        u'rows': [[u'10', u'test 10']],
        })

    utils.vtgate.vtclient(
        'update vt_user_extra set email=:v2 where user_id = :v1',
        bindvars=[10, 'test 1000'])

    out, _ = utils.vtgate.vtclient(
        'select user_id, email from vt_user_extra where user_id = :v1',
        bindvars=[10], streaming=True, json_output=True)
    self.assertEqual(out, {
        u'fields': [u'user_id', u'email'],
        u'rows': [[u'10', u'test 1000']],
        })

    utils.vtgate.vtclient(
        'delete from vt_user_extra where user_id = :v1', bindvars=[10])

    out, _ = utils.vtgate.vtclient(
        'select user_id, email from vt_user_extra where user_id = :v1',
        bindvars=[10], json_output=True)
    self.assertEqual(out, {
        u'fields': [u'user_id', u'email'],
        u'rows': None,
        })

    # check that specifying an invalid keyspace is propagated and triggers an
    # error
    _, err = utils.vtgate.vtclient(
        'insert into vt_user_extra(user_id, email) values (:v1, :v2)',
        keyspace='invalid',
        bindvars=[10, 'test 10'],
        raise_on_error=False)
    self.assertIn('keyspace invalid not found in vschema', err)

  def test_vtctl_vtgate_execute(self):
    """This test uses 'vtctl VtGateExecute' to send and receive various queries.
    """
    utils.vtgate.execute(
        'insert into vt_user_extra(user_id, email) values (:user_id, :email)',
        bindvars={'user_id': 11, 'email': 'test 11'})

    qr = utils.vtgate.execute(
        'select user_id, email from vt_user_extra where user_id = :user_id',
        bindvars={'user_id': 11})
    logging.debug('Original row: %s', str(qr))
    self.assertEqual(qr['fields'][0]['name'], 'user_id')
    self.assertEqual(len(qr['rows']), 1)
    v = qr['rows'][0][1]
    self.assertEqual(v, 'test 11')

    # test using exclude_field_names works.
    qr = utils.vtgate.execute(
        'select user_id, email from vt_user_extra where user_id = :user_id',
        bindvars={'user_id': 11}, execute_options='included_fields:TYPE_ONLY ')
    logging.debug('Original row: %s', str(qr))
    self.assertNotIn('name', qr['fields'][0])
    self.assertEqual(len(qr['rows']), 1)
    v = qr['rows'][0][1]
    self.assertEqual(v, 'test 11')

    utils.vtgate.execute(
        'update vt_user_extra set email=:email where user_id = :user_id',
        bindvars={'user_id': 11, 'email': 'test 1100'})

    qr = utils.vtgate.execute(
        'select user_id, email from vt_user_extra where user_id = :user_id',
        bindvars={'user_id': 11})
    logging.debug('Modified row: %s', str(qr))
    self.assertEqual(len(qr['rows']), 1)
    v = qr['rows'][0][1]
    self.assertEqual(v, 'test 1100')

    utils.vtgate.execute(
        'delete from vt_user_extra where user_id = :user_id',
        bindvars={'user_id': 11})

    qr = utils.vtgate.execute(
        'select user_id, email from vt_user_extra where user_id = :user_id',
        bindvars={'user_id': 11})
    self.assertEqual(len(qr['rows'] or []), 0)

  def test_split_query(self):
    """This test uses 'vtctl VtGateSplitQuery' to validate the Map-Reduce APIs.

    We want to return KeyRange queries.
    """
    sql = 'select id, name from vt_user'
    s = utils.vtgate.split_query(sql, 'user', 2)
    self.assertEqual(len(s), 2)
    first_half_queries = 0
    second_half_queries = 0
    for q in s:
      self.assertEqual(q['query']['sql'], sql)
      self.assertIn('key_range_part', q)
      self.assertEqual(len(q['key_range_part']['key_ranges']), 1)
      kr = q['key_range_part']['key_ranges'][0]
      eighty_in_base64 = 'gA=='
      is_first_half = 'start' not in kr and kr['end'] == eighty_in_base64
      is_second_half = 'end' not in kr and kr['start'] == eighty_in_base64
      self.assertTrue(is_first_half or is_second_half,
                      'invalid keyrange %s' % str(kr))
      if is_first_half:
        first_half_queries += 1
      else:
        second_half_queries += 1
    self.assertEqual(first_half_queries, 1, 'invalid split %s' % str(s))
    self.assertEqual(second_half_queries, 1, 'invalid split %s' % str(s))

  def test_vschema_vars(self):
    """Tests the variables exported by vtgate.

    This test needs to run as the last test, as it depends on what happened
    previously.
    """
    v = utils.vtgate.get_vars()
    self.assertIn('VtgateVSchemaCounts', v)
    self.assertIn('Reload', v['VtgateVSchemaCounts'])
    self.assertGreater(v['VtgateVSchemaCounts']['Reload'], 0)
    self.assertNotIn('WatchError', v['VtgateVSchemaCounts'], 0)
    self.assertNotIn('Parsing', v['VtgateVSchemaCounts'])

if __name__ == '__main__':
  utils.main()
