#!/usr/bin/env bash
function find_singularity_files_deps() {
	# Find all files that are dependencies of a Singularity definition file.
	local __deffile="$1"
	local __curdir="${PWD}"
	echo "$(cd "$(dirname "${__deffile}")" && sed -nE '1,/^\s*%files\b/d; /^\s*%.*/q; s/^\s*//g; s/([^\])\s+.*$/\1/g; /^\s*$/d; p' "$(basename ${__deffile})" | paste -sd ' ' | xargs find | xargs realpath --logical --no-symlinks --relative-to="${__curdir}" | sort | uniq)"
}
