
v1AAA=1aaa
v1aaa=1xxx
v1BBB=$(v1AAA)
v1CCC=$(v$(v1BBB))


v2AAA:=2aaa
v2aaa:=2xxx
v2BBB:=$(v2AAA)
v2CCC:=$(v$(v2BBB))



v3AAA=v3aaa
v3BBB=$(v3AAA)
v3CCC:=$(v3AAA)
v3AAA=v3xxx
