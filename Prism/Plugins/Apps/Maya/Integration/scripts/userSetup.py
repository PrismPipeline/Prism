
# >>>PrismStart
try:
    import PrismInit
    global pcore
    pcore = PrismInit.prismInit(skipBatch=True)
except:
    import traceback
    print("Error occured while loading Prism:\n\n%s" % traceback.format_exc())
# <<<PrismEnd
