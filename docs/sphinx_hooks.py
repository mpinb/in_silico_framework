from config.isf_logging import logger as isf_logger
logger = isf_logger.getChild("DOCS")
logger.setLevel("INFO")

DOCS_STATS = {
    what: {'included': 0, 'documented': 0, 'skipped': 0}
    for what in ['method', 'function', 'class', 'module', 'package', 'data', 'attribute', 'property', 'exception']
}
LAST_PARENT_TO_SKIP = "NO_PARENT"

def count_documented_members(app, what, name, obj, skip, options):
    """Count the number of documented members.
    
    Args:
        obj (autoapidoc._objects.Python*): autoapi object
    """
    
    global DOCS_STATS
    global LAST_PARENT_TO_SKIP
    # skip special members, except __get__ and __set__
    short_name = name.rsplit('.', 1)[-1]
    # don't count undocumented special members, except __get__ and __set__
    if short_name.startswith('__') and short_name.endswith('__') and name not in ['__get__', '__set__']:
        DOCS_STATS[what]['skipped'] += 1
        return
    # Do not count if it has the :skip-doc: tag
    elif not obj.is_undoc_member and ':skip-doc:' in obj.docstring:
        LAST_PARENT_TO_SKIP = obj.id
        logger.debug("    Ignoring empty docstrings for children of {}".format(obj.id))
        DOCS_STATS[what]['skipped'] += 1
        return
    
    # dont double count inherited members
    elif obj.inherited:
        DOCS_STATS[what]['skipped'] += 1
        return

    # Skip if it was skipped at conf level.
    # elif name in modules_to_skip:
    #     return

    # the parent object of this one is skipped, so don't count this one either.
    elif LAST_PARENT_TO_SKIP in obj.id:
        DOCS_STATS[what]['skipped'] += 1
        return
    
    elif what in ['method', 'function', 'class', 'module', 'package']:
        DOCS_STATS[what]['included'] += 1
        if obj.docstring and obj.docstring.strip():
            DOCS_STATS[what]['documented'] += 1
        else:
            logger.warning(f"Undocumented member: {what}: {name}")
    return
    
    
def log_documented_members(app, env):
    """Log the number of documented members."""
    global DOCS_STATS
    logger.info(f"Skipped members: {DOCS_STATS['method']['skipped']} methods, {DOCS_STATS['function']['skipped']} functions, {DOCS_STATS['class']['skipped']} classes, {DOCS_STATS['module']['skipped']} modules, {DOCS_STATS['package']['skipped']} packages")
    logger.info(f"Total skipped: {sum([DOCS_STATS[what]['skipped'] for what in DOCS_STATS])}")
    logger.info("Members are skipped if they:\n\
        - Are special members, except __get__ and __set__\n\
        - Have the :skip-doc: tag in their docstring\n\
        - Are inherited\n\
        - Are children of a parent that was skipped\n\
        - Are in the list of modules to skip (but those are not counted here)")
    for what in DOCS_STATS:
        documented, included = DOCS_STATS[what]['documented'], DOCS_STATS[what]['included']
        coverage_what = 100 * documented / included if included > 0 else 0
        logger.info(f"Documented {what}s: {documented}/{included} ({coverage_what:.2f}%)")
        logger.info(f"Skipped {what}s: {DOCS_STATS[what]['skipped']} not included")
    total_documented, total_included = sum([DOCS_STATS[what]['documented'] for what in DOCS_STATS]), sum([DOCS_STATS[what]['included'] for what in DOCS_STATS])
    logger.info(f"Total documented: {total_documented}/{total_included} ({100 * total_documented / total_included:.2f}%)")


def find_first_match(lines, substring):
    for i, line in enumerate(lines):
        if substring in line:
            return i
    return -1