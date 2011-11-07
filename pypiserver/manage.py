
import sys, os, xmlrpclib, pkg_resources
from pypiserver import core


class pkgfile(object):
    def __init__(self, path):
        self.path = path
        self.pkgname, self.version = core.guess_pkgname_and_version(path)
        self.version_info = pkg_resources.parse_version(self.version)


def is_stable_version(pversion):
    for x in pversion:
        if x.startswith("*final"):
            return True
        if x.startswith("*"):
            return False
    return False


def filter_stable_releases(releases):
    res = []
    for pversion, version in releases:
        if is_stable_version(pversion):
            res.append((pversion, version))
    return res


def find_updates(pkgset, stable_only=True):
    no_releases = set()

    def write(s):
        sys.stdout.write(s)
        sys.stdout.flush()

    pypi = xmlrpclib.Server("http://pypi.python.org/pypi/")
    pkgname2latest = {}

    pkgfiles = [pkgfile(x) for x in pkgset.find_packages()]

    for x in pkgfiles:
        if x.pkgname not in pkgname2latest:
            pkgname2latest[x.pkgname] = x
        elif x.version_info > pkgname2latest[x.pkgname].version_info:
            pkgname2latest[x.pkgname] = x

    need_update = []

    sys.stdout.write("checking %s packages for newer version\n" % len(pkgname2latest),)
    for count, (pkgname, file) in enumerate(pkgname2latest.items()):
        if count % 40 == 0:
            write("\n")

        releases = pypi.package_releases(pkgname)

        releases = [(pkg_resources.parse_version(x), x) for x in releases]
        if stable_only:
            releases = filter_stable_releases(releases)

        status = "."
        if releases:
            m = max(releases)
            if m[0] > file.version_info:
                file.latest_version = m[1]
                status = "u"
                # print "%s needs update from %s to %s" % (pkgname, file.version, m[1])
                need_update.append(file)
        else:
            no_releases.add(pkgname)
            status = "e"

        write(status)

    write("\n\n")

    no_releases = list(no_releases)
    no_releases.sort()
    sys.stdout.write("no releases found on pypi for " + ", ".join(no_releases) + "\n\n")
    return need_update


def update(pkgset, destdir=None, dry_run=False, stable_only=True):
    need_update = find_updates(pkgset, stable_only=stable_only)
    for x in need_update:
        sys.stdout.write("# update " + x.pkgname + " from " + x.version + "to" + x.latest_version + "\n")

        cmd = ["pip", "-q", "install", "-i", "http://pypi.python.org/simple",
               "-d", destdir or os.path.dirname(os.path.join(pkgset.root, x.path)),
               "%s==%s" % (x.pkgname, x.latest_version)]

        sys.stdout.write(" ".join(cmd) + "\n\n")
        if not dry_run:
            os.spawnlp(os.P_WAIT, cmd[0], *cmd)


def main():
    root = sys.argv[1]
    if len(sys.argv) > 2:
        destdir = sys.argv[2]
    else:
        destdir = None

    update(core.pkgset(root), destdir, True)


if __name__ == "__main__":
    main()