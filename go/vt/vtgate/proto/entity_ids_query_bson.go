// Copyright 2012, Google Inc. All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

package proto

// DO NOT EDIT.
// FILE GENERATED BY BSONGEN.

import (
	"bytes"

	"github.com/youtube/vitess/go/bson"
	"github.com/youtube/vitess/go/bytes2"
)

// MarshalBson bson-encodes EntityIdsQuery.
func (entityIdsQuery *EntityIdsQuery) MarshalBson(buf *bytes2.ChunkedWriter, key string) {
	bson.EncodeOptionalPrefix(buf, bson.Object, key)
	lenWriter := bson.NewLenWriter(buf)

	bson.EncodeString(buf, "Sql", entityIdsQuery.Sql)
	// map[string]interface{}
	{
		bson.EncodePrefix(buf, bson.Object, "BindVariables")
		lenWriter := bson.NewLenWriter(buf)
		for _k, _v1 := range entityIdsQuery.BindVariables {
			bson.EncodeInterface(buf, _k, _v1)
		}
		lenWriter.Close()
	}
	bson.EncodeString(buf, "Keyspace", entityIdsQuery.Keyspace)
	bson.EncodeString(buf, "EntityColumnName", entityIdsQuery.EntityColumnName)
	// []EntityId
	{
		bson.EncodePrefix(buf, bson.Array, "EntityKeyspaceIDs")
		lenWriter := bson.NewLenWriter(buf)
		for _i, _v2 := range entityIdsQuery.EntityKeyspaceIDs {
			_v2.MarshalBson(buf, bson.Itoa(_i))
		}
		lenWriter.Close()
	}
	entityIdsQuery.TabletType.MarshalBson(buf, "TabletType")
	// *Session
	if entityIdsQuery.Session == nil {
		bson.EncodePrefix(buf, bson.Null, "Session")
	} else {
		(*entityIdsQuery.Session).MarshalBson(buf, "Session")
	}

	lenWriter.Close()
}

// UnmarshalBson bson-decodes into EntityIdsQuery.
func (entityIdsQuery *EntityIdsQuery) UnmarshalBson(buf *bytes.Buffer, kind byte) {
	switch kind {
	case bson.EOO, bson.Object:
		// valid
	case bson.Null:
		return
	default:
		panic(bson.NewBsonError("unexpected kind %v for EntityIdsQuery", kind))
	}
	bson.Next(buf, 4)

	for kind := bson.NextByte(buf); kind != bson.EOO; kind = bson.NextByte(buf) {
		switch bson.ReadCString(buf) {
		case "Sql":
			entityIdsQuery.Sql = bson.DecodeString(buf, kind)
		case "BindVariables":
			// map[string]interface{}
			if kind != bson.Null {
				if kind != bson.Object {
					panic(bson.NewBsonError("unexpected kind %v for entityIdsQuery.BindVariables", kind))
				}
				bson.Next(buf, 4)
				entityIdsQuery.BindVariables = make(map[string]interface{})
				for kind := bson.NextByte(buf); kind != bson.EOO; kind = bson.NextByte(buf) {
					_k := bson.ReadCString(buf)
					var _v1 interface{}
					_v1 = bson.DecodeInterface(buf, kind)
					entityIdsQuery.BindVariables[_k] = _v1
				}
			}
		case "Keyspace":
			entityIdsQuery.Keyspace = bson.DecodeString(buf, kind)
		case "EntityColumnName":
			entityIdsQuery.EntityColumnName = bson.DecodeString(buf, kind)
		case "EntityKeyspaceIDs":
			// []EntityId
			if kind != bson.Null {
				if kind != bson.Array {
					panic(bson.NewBsonError("unexpected kind %v for entityIdsQuery.EntityKeyspaceIDs", kind))
				}
				bson.Next(buf, 4)
				entityIdsQuery.EntityKeyspaceIDs = make([]EntityId, 0, 8)
				for kind := bson.NextByte(buf); kind != bson.EOO; kind = bson.NextByte(buf) {
					bson.SkipIndex(buf)
					var _v2 EntityId
					_v2.UnmarshalBson(buf, kind)
					entityIdsQuery.EntityKeyspaceIDs = append(entityIdsQuery.EntityKeyspaceIDs, _v2)
				}
			}
		case "TabletType":
			entityIdsQuery.TabletType.UnmarshalBson(buf, kind)
		case "Session":
			// *Session
			if kind != bson.Null {
				entityIdsQuery.Session = new(Session)
				(*entityIdsQuery.Session).UnmarshalBson(buf, kind)
			}
		default:
			bson.Skip(buf, kind)
		}
	}
}
