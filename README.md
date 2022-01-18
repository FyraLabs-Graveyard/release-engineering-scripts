# Release Engineering Scripts

A collection of release engineering scripts to make our lives easier when working on Ultramarine releases. Essentially an extension of umpkg but for the whole release instead of just one package.

This is written for the Ultramarine Linux Release Engineering team, and (possibly) future forks of it. It is not intended for general use, but for developers.

Everything is licensed under the [MIT license](LICENSE)

## Scripts
- monosplit: Splits an RPM spec monorepo into individual git repositories. (Can also be used to quickly create a new umpkg repo.)
- massrebuild: Does a mass rebuild from one Koji tag to another. Useful for bumping versions. (only use every half year, because Fedora upstream)

## Ansible Playbooks
- compose: Composes a release from a koji tag (run this on a background terminal, it will take a while, and waste some space)
