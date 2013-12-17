from .helpers import groupby
import re
import itertools as it


class Relationship(object):
    """Abstract Class for the various rel strategies"""

    def __str__(self):
        m = re.search("^(\w).+2(\w).+$", type(self).__name__)
        return '{0}2{1}'.format(m.group(1), m.group(2))


class RelationshipError(Exception):pass


class one2one(Relationship):
    @classmethod
    def gen_tasks(klass, stage):
        for parent_task in it.chain(*[s.tasks for s in stage.parents]):
            tags2 = parent_task.tags.copy()
            tags2.update(stage.extra_tags)
            new_task = stage.task(stage=stage, tags=tags2)
            yield new_task, [parent_task]


class many2one(Relationship):
    def __init__(self, keywords):
        assert isinstance(keywords, list), '`keywords` must be a list'
        self.keywords = keywords

    @classmethod
    def gen_tasks(klass, stage):
        for tags, parent_task_group in many2one.reduce(stage, stage.rel.keywords):
            tags.update(stage.extra_tags)
            new_task = stage.task(stage=stage, tags=tags)
            yield new_task, parent_task_group

    @classmethod
    def reduce(cls, stage, keywords):
        if type(keywords) != list:
            raise TypeError('keywords must be a list')
        if any(k == '' for k in keywords):
            raise TypeError('keyword cannot be an empty string')

        parent_tasks = list(it.chain(*[s.tasks for s in stage.parents]))
        parent_tasks_without_all_keywords = filter(lambda t: not all([k in t.tags for k in keywords]),
                                                   parent_tasks)
        parent_tasks_with_all_keywords = filter(lambda t: all(k in t.tags for k in keywords), parent_tasks)

        if len(parent_tasks_with_all_keywords) == 0:
            raise RelationshipError, 'Parent stages must have at least one task with all many2one keywords of {0}'.format(
                keywords)

        for tags, parent_task_group in groupby(parent_tasks_with_all_keywords,
                                               lambda t: dict((k, t.tags[k]) for k in keywords if k in t.tags)):
            parent_task_group = list(parent_task_group) + parent_tasks_without_all_keywords
            yield tags, parent_task_group


class one2many(Relationship):
    def __init__(self, split_by):
        one2many.validate_split_by(split_by)
        self.split_by = split_by

    @classmethod
    def validate_split_by(cls, split_by):
        assert isinstance(split_by, list), '`split_by` must be a list'
        if len(split_by) > 0:
            assert isinstance(split_by[0], tuple), '`split_by` must be a list of tuples'
            assert isinstance(split_by[0][0], str), 'the first element of tuples in `split_by` must be a str'
            assert isinstance(split_by[0][1],
                              list), 'the second element of the tuples in the `split_by` list must also be a list'

    @classmethod
    def gen_tasks(klass, stage):
        for parent_task in it.chain(*[s.tasks for s in stage.parents]):
            for tags in one2many.split(stage.rel.split_by):
                tags.update(parent_task.tags)
                tags.update(stage.extra_tags)
                new_task = stage.task(stage=stage, tags=tags)
                yield new_task, [parent_task]

    @classmethod
    def split(cls, split_by):
        splits = [list(it.product([split[0]], split[1])) for split in split_by]
        for new_tags in it.product(*splits):
            new_tags = dict(new_tags)
            yield new_tags


class many2many(Relationship):
    def __init__(self, keywords, split_by):
        one2many.validate_split_by(split_by)
        self.split_by = split_by
        assert isinstance(keywords, list), '`keywords` must be a list'
        self.keywords = keywords

    @classmethod
    def gen_tasks(klass, stage):
        for tags, parent_task_group in many2many.reduce_split(stage):
            tags.update(stage.extra_tags)
            new_task = stage.task(stage=stage, tags=tags)
            yield new_task, parent_task_group

    @classmethod
    def reduce_split(klass, stage):
        for tags, parent_task_group in many2one.reduce(stage, stage.rel.keywords):
            print tags, stage.rel.split_by
            for new_tags in one2many.split(stage.rel.split_by):
                new_tags.update(tags)
                yield new_tags, parent_task_group