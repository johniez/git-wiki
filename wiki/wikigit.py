"""
    Wiki core using Git as storage
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
from wiki.core import Wiki
from wiki.core import Processors
from wiki.core import Page
from wiki import named_locks
import datetime
import git
import os


class WikiGit(Wiki):
    class Commit(object):
        log_formatter = "%h%x00%at%x00%an"

        def __init__(self, commit_hash, commit_timestamp, commit_author,
                     commit_data=None):
            self.commit = commit_hash
            self.timestamp = datetime.datetime.fromtimestamp(
                int(commit_timestamp))
            self.author = commit_author
            self.data = commit_data

        @staticmethod
        def from_gitlog(string):
            data = string.split('\0')
            return WikiGit.Commit(data[0], data[1], data[2])

        def highlite_diff(self):
            if self.data:
                return Processors.highlite_diff(self.data)
            return ""

    def __init__(self, root):
        super(WikiGit, self).__init__(root)
        self.repo = git.Repo(root).git
        named_locks.set_lock('git-lock', os.path.join(root, 'wikigit.flock'))

    @named_locks.interprocess_lock('git-lock')
    def load(self, url):
        """Load content, waiting for merge to complete."""
        return super(WikiGit, self).load(url)

    @named_locks.interprocess_lock('git-lock')
    def save(self, url, body, meta, author=None):
        """
        Save file and commit changes to the repository.
        Current approach is very stupid, overwriting previous changes if
        commit is not the latest one for that file.

        Solution can be (if parent commit is known):
          * git checkout -b changes
          * git reset --hard $parent
          * write new file content - save(url, body, meta)
          * git commit -am $commit_message
          * git merge master
        On error (conflict), return to the master branch:
            * read file content to merge by user
            * git reset --hard
            * git checkout master
            * git branch -D changes
            * and deliver previously read content to the user to resolve merge
        On success:
            * git checkout master
            * git merge changes
            * git branch -D changes
        """
        super(WikiGit, self).save(url, body, meta)
        self.repo.add(url + '.md')
        author = author or 'anonymouse'
        author += ' <' + author + '>'
        self.repo.commit(m="changed", author=author)

    @named_locks.interprocess_lock('git-lock')
    def move(self, url, newurl):
        """Rename url's file inside a repository."""
        self.repo.mv(url + '.md', newurl + '.md')
        self.repo.commit(m="file moved")

    @named_locks.interprocess_lock('git-lock')
    def delete(self, url):
        """Delete url's file from repository."""
        if not self.exists(url):
            return False
        self.repo.rm(url + '.md')
        self.repo.commit(m="file deleted")
        return True

    def get_or_404(self, url):
        page = super(WikiGit, self).get_or_404(url)
        page.history = self.history(url)
        return page

    def history(self, url, offset=0, limit=5):
        # TODO catch git.exc.GitCommandError and raise 404 or 500
        return [
            self.Commit.from_gitlog(rec)
            for rec in self.repo.log(
                url + '.md',
                format=self.Commit.log_formatter).split('\n')
        ][offset:limit]

    def show(self, commit):
        # TODO catch git.exc.GitCommandError and raise 404 or 500
        data = self.repo.show(
            commit, '-M9',
            pretty="format:" + self.Commit.log_formatter + '%x00',
        ).split('\0')
        return self.Commit(data[0], data[1], data[2], data[3].strip())

    def search(self, term, ignore_case=True):
        try:
            results = self.repo.grep(term, G=True, i=ignore_case).split('\n')
            # split filename:match for file names only (matched text can be
            # used to output in the future).
            return [Page(self, r.split(':')[0][:-3]) for r in results]
        except git.exc.GitCommandError:
            return super(WikiGit, self).search(term)
