#!/usr/bin/env python
import unittest
import datetime
from autumn.model import Model
from autumn.fields import *  
from autumn.db.relations import *
from autumn.tests.models import Book, Author
from autumn.db.query import Query
from autumn.db import escape
from autumn import validators

class TestModels(unittest.TestCase):
        
    def testmodel(self):
        # Create tables
        
        ### MYSQL ###
        #
        # DROP TABLE IF EXISTS author;
        # CREATE TABLE author (
        #     id INT(11) NOT NULL auto_increment,
        #     first_name VARCHAR(40) NOT NULL,
        #     last_name VARCHAR(40) NOT NULL,
        #     bio TEXT,
        #     PRIMARY KEY (id)
        # );
        # DROP TABLE IF EXISTS books;
        # CREATE TABLE books (
        #     id INT(11) NOT NULL auto_increment,
        #     title VARCHAR(255),
        #     author_id INT(11),
        #     FOREIGN KEY (author_id) REFERENCES author(id),
        #     PRIMARY KEY (id)
        # );
        
        ### SQLITE ###
        #
        sqlite_create = """
         DROP TABLE IF EXISTS author;
         DROP TABLE IF EXISTS books;
         CREATE TABLE author (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           first_name VARCHAR(40) NOT NULL,
           last_name VARCHAR(40) NOT NULL,
           bio TEXT,
         );
         CREATE TABLE books (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           title VARCHAR(255),
           author_id INT(11),
           json_data TEXT, 
           FOREIGN KEY (author_id) REFERENCES author(id)
         );
        """
        #autumn_db.conn.connect('sqlite3', ':memory:')
        #Query.raw_sql(sqlite_create)
        
        for table in ('author', 'books'):
            Query.raw_sql('DELETE FROM %s' % escape(table))
        
        # Test Creation
        assert Author.objects.query().count() == 0
        
        james = Author(first_name='James', last_name='Joyce')
        james.save()
        
        assert Author.objects.query().count() == 1
        
        kurt = Author(first_name='Kurt', last_name='Vonnegut')
        kurt.save()
        
        tom = Author(first_name='Tom', last_name='Robbins')
        tom.save()
        #print "Tom ID", tom.id
        Book(title='Ulysses', author_id=james.id).save()
        Book(title='Slaughter-House Five', author_id=kurt.id).save()
        Book(title='Jitterbug Perfume', author_id=tom.id).save()
        slww = Book(title='Still Life with Woodpecker', author_id=tom.id, json_data=['some','data'])
        slww.save()
        
        self.assertEqual(Book.objects.get(slww.id).json_data[0], 'some')
        # Test ForeignKey
        self.assertEqual(slww.author.first_name, 'Tom')
        
        # Test OneToMany
        self.assertEqual(len(list(tom.books)), 2)
        
        kid = kurt.id
        del(james, kurt, tom, slww)
        
        # Test retrieval
        b = Book.objects.query(title='Ulysses')[0]
        
        a = Author.objects.get(b.author_id)
        self.assertEqual(a.id, b.author_id)
        
        a = Author.objects.query(id=b.id)[:]
        self.assert_(isinstance(a, list))
        
        # Test update
        new_last_name = 'Vonnegut, Jr.'
        a = Author.objects.query(id=kid)[0]
        a.last_name = new_last_name
        a.save()
        
        a = Author.objects.get(kid)
        self.assertEqual(a.last_name, new_last_name)
        
        # Test count
        self.assertEqual(Author.objects.query().count(), 3)
        
        self.assertEqual(len(Book.objects.query()[1:4]), 3)
        
        # Test delete
        a.delete()
        self.assertEqual(Author.objects.query().count(), 2)
        
        # Test validation
        a = Author(first_name='', last_name='Ted')
        try:
            a.save()
            raise Exception('Validation not caught')
        except Model.ValidationError:
            pass
        
        # Test defaults
        a.first_name = 'Bill and'
        a.save()
        self.assertEqual(a.bio, 'No bio available')
        
        try:
            Author(first_name='I am a', last_name='BadGuy!').save()
            raise Exception('Validation not caught')
        except Model.ValidationError:
            pass
            
    def testvalidators(self):
        ev = validators.Email()
        assert ev('test@example.com')
        assert not ev('adsf@.asdf.asdf')
        assert validators.Length()('a')
        assert not validators.Length(2)('a')
        assert validators.Length(max_length=10)('abcdegf')
        assert not validators.Length(max_length=3)('abcdegf')

        n = validators.Number(1, 5)
        assert n(2)
        assert not n(6)
        assert validators.Number(1)(100.0)
        assert not validators.Number()('rawr!')

        vc = validators.ValidatorChain(validators.Length(8), validators.Email())
        assert vc('test@example.com')
        assert not vc('a@a.com')
        assert not vc('asdfasdfasdfasdfasdf')
        
    def testormlite_port(self):

        class Foo(Model):
            class Meta:
                fields = [IdField('id'), IntegerField('moo'), PickleField('pickle')]
            bar_set = OneToMany('Bar')
    
        class Bar(Model):
            class Meta:
                fields = [IdField('id'), 
                          IntegerField('foo_id'), 
                          JSONField('json_array', notnull=False)]
            foo = ForeignKey(Foo)
    
        Foo.objects.create_table()
        Bar.objects.create_table()
        #c.execute("create table foo (id integer primary key, moo integer, pickle TEXT)")
        #c.execute("create table bar (id integer primary key, foo_id integer, json_array TEXT)")
        #c.execute("create table foo (id integer primary key AUTOINCREMENT, moo integer, pickle TEXT)")
        #c.execute("create table bar (id integer primary key AUTOINCREMENT, foo_id integer, json_array TEXT)")
        
        #print dir(Foo())
        f = Foo(id=1, moo=2, pickle={'a':'b'})
        f.save()
        assert 'a' in Foo.objects.get(1).pickle
    
        Foo(id=2,cow=3, moo=2).save()
        b = Bar(id=1,foo_id=1)
        b.save()
        b = Bar(id=2,foo_id=1,json_array=[1,2,3])
        b.save()
        for o in Foo.objects.query():
            #print "Fetch:", o
            assert o.moo == 2
            assert o.id != 3
        
        assert b.foo != None
        #print ",".join(map(str,f.bar_set.fetchall()))
        assert len(list(f.bar_set)) == 2
        b = Bar.objects.get(2)
        assert b.foo_id == 1
        #print c.execute("select * from bar").fetchall()
        #print b.json_array, len(b.json_array), type(b.json_array)
        assert len(b.json_array) == 3
        assert sum(b.json_array) == 6
        
        for b in Bar.objects.cursor().execute("select foo_id from bar"):
            #print b
            assert b.id == None
            assert b.foo_id == 1
            
        b = Bar.objects.get(2)
        b.delete()
        assert len(Bar.objects.query()) == 1
    
        f = Foo(moo=2, pickle={'a':'b'})
        f.save()
        #print id 
        assert f.id == 3
        
        class Dud(Model):
            class Meta:
                fields = [TextField('a',primary_key=True), TextField('b',primary_key=True)]
        
        #print Bar.objects.tabledef()
        #print Dud.objects.tabledef()
        
        Dud.objects.create_table()
        
        Dud(a="a",b="b").save()
        d = None
        try:
            d = Dud(a="a",b="b").save()
        except:
            pass
        # TODO handle multiple primary keys 
        # assert d == None 
            
        #print "Passed"
        
        fields = 0 
        #print "Iterating..."
        for k, v in f.items():
            fields += 1
            #print k, v
            
        assert fields == len(Foo._fields)
        
if __name__ == '__main__':
    unittest.main()
