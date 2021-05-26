from ape_safe import ApeSafe
from brownie import web3

THE_KEEP3R = "0x0D5Dc686d0a2ABBfDaFDFb4D0533E886517d4E83" # msig address

def sushi_to_xsushi():
    '''
        Pull SUSHI rewards from KP3R-ETH and stake them as xSUSHI
    '''
    safe = ApeSafe("0x0D5Dc686d0a2ABBfDaFDFb4D0533E886517d4E83")

    assert safe.address == THE_KEEP3R

    # contracts from https://docs.unit.xyz/docs/contracts
    unit_vault = safe.contract("0xb1cFF81b9305166ff1EFc49A129ad2AfCd7BCf19")
    unit_cdp_manager = safe.contract("0x0e13ab042eC5AB9Fc6F43979406088B9028F66fA")

    sushi_chief = safe.contract("0xc2EdaD668740f1aA35E4D8f227fB8E17dcA888Cd")

    sushi = safe.contract("0x6B3595068778DD592e39A122f4f5a5cF09C90fE2")
    xsushi = safe.contract("0x8798249c2E607446EfB7Ad49eC89dD1865Ff4272")
    usdp = safe.contract('0x1456688345527bE1f37E9e627DA0837D6f08C925')
    # curve
    curve_usdp_pool = safe.contract('0x42d7025938bEc20B69cBae5A77421082407f053A')
    curve_usdp_lp = safe.contract('0x7Eb40E450b9655f4B3cC4259BCC731c63ff55ae6')
    # yearn
    yusdp3crv = safe.contract('0xC4dAf3b5e2A9e93861c3FBDd25f1e943B8D87417')

    # restake sushi in xsushi
    _pid = 58 # KP3R-ETH
    sushi_chief.deposit(_pid, 0) # claims sushi

    assert sushi.balanceOf(safe.address) > 0

    sushi.approve(xsushi, sushi.balanceOf(safe.address))
    xsushi.enter(sushi.balanceOf(safe.address))

    safe_tx = safe.multisend_from_receipts()
    safe.preview(safe_tx, call_trace=True)
    safe.post_transaction(safe_tx)


def sushi_to_usdp():
    '''
        Pull SUSHI rewards from KP3R-ETH, stake them as xSUSHI and pull USDP from unit
    '''
    safe = ApeSafe("thekeep3r.eth")

    assert safe.address == THE_KEEP3R

    # contracts from https://docs.unit.xyz/docs/contracts
    unit_vault = safe.contract("0xb1cFF81b9305166ff1EFc49A129ad2AfCd7BCf19")
    unit_cdp_manager = safe.contract("0x0e13ab042eC5AB9Fc6F43979406088B9028F66fA")
    unit_cdp_viewer = safe.contract("0x6C3B5C2477AE2BcF9C4244BC8A019a8f6f4eC231")

    sushi_chief = safe.contract("0xc2EdaD668740f1aA35E4D8f227fB8E17dcA888Cd")

    sushi = safe.contract("0x6B3595068778DD592e39A122f4f5a5cF09C90fE2")
    xsushi = safe.contract("0x8798249c2E607446EfB7Ad49eC89dD1865Ff4272")
    usdp = safe.contract('0x1456688345527bE1f37E9e627DA0837D6f08C925')
    # curve
    curve_usdp_pool = safe.contract('0x42d7025938bEc20B69cBae5A77421082407f053A')
    curve_usdp_lp = safe.contract('0x7Eb40E450b9655f4B3cC4259BCC731c63ff55ae6')
    # yearn
    yusdp3crv = safe.contract('0xC4dAf3b5e2A9e93861c3FBDd25f1e943B8D87417')

    # restake sushi in xsushi
    _pid = 58 # KP3R-ETH
    sushi_chief.deposit(_pid, 0) # claims sushi

    assert sushi.balanceOf(safe.address) > 0

    sushi.approve(xsushi, sushi.balanceOf(safe.address))
    xsushi.enter(sushi.balanceOf(safe.address))

    # open unit cdp, lock all xsushi, and draw usdp
    lock_xsushi = xsushi.balanceOf(safe.address)
    draw_usdp = 136_000 * 10 ** usdp.decimals() # TODO:
    xsushi.approve(unit_vault, lock_xsushi)
    # NOTE: need approval to vault address
    unit_cdp_manager.join(xsushi, lock_xsushi, draw_usdp)

    assert xsushi.balanceOf(safe.address) == 0 # all xsushi locked

    # deposit into curve lp
    amounts = [draw_usdp, 0]
    mint_amount = curve_usdp_pool.calc_token_amount(amounts, True)
    usdp.approve(curve_usdp_pool, draw_usdp)
    curve_usdp_pool.add_liquidity(amounts, mint_amount * 0.99) # 1 % slippage

    assert curve_usdp_lp.balanceOf(safe.address) > 0 # lp tokens acquired

    # deposit into yearn vault
    curve_usdp_lp.approve(yusdp3crv, curve_usdp_lp.balanceOf(safe.account))
    yusdp3crv.deposit(curve_usdp_lp.balanceOf(safe.account))

    cdp_parameters = unit_cdp_viewer.getCollateralParameters(xsushi, safe.address)
    xsushi_locked = cdp_parameters["cdp"]["collateral"]
    usdp_minted = cdp_parameters["cdp"]["debt"]

    liquidation_price = unit_cdp_manager.liquidationPrice_q112(xsushi, safe.account) / unit_cdp_manager.Q112()
    print("Liquidation price:", liquidation_price)

    # doesn't hold true for consecutive lockups
    # assert xsushi_locked == lock_xsushi
    # assert usdp_minted == draw_usdp

    print ("xsushi locked:", xsushi_locked)
    print ("usdp minted:", usdp_minted)

    safe_tx = safe.multisend_from_receipts()
    safe.preview(safe_tx, call_trace=True)
    safe.post_transaction(safe_tx)


def repay_xsushi_usdp():
    '''
        Repay USDP debt and pull xSUSHI out
    '''

    safe = ApeSafe("0x0D5Dc686d0a2ABBfDaFDFb4D0533E886517d4E83")

    assert safe.address == THE_KEEP3R

    # contracts from https://docs.unit.xyz/docs/contracts
    unit_vault =  safe.contract('0xb1cFF81b9305166ff1EFc49A129ad2AfCd7BCf19')
    unit_cdp_manager = safe.contract("0x0e13ab042eC5AB9Fc6F43979406088B9028F66fA")
    unit_cdp_viewer = safe.contract("0x6C3B5C2477AE2BcF9C4244BC8A019a8f6f4eC231")

    xsushi = safe.contract("0x8798249c2E607446EfB7Ad49eC89dD1865Ff4272")
    usdp = safe.contract('0x1456688345527bE1f37E9e627DA0837D6f08C925')
    # curve
    curve_usdp_pool = safe.contract('0x42d7025938bEc20B69cBae5A77421082407f053A')
    curve_usdp_lp = safe.contract('0x7Eb40E450b9655f4B3cC4259BCC731c63ff55ae6')
    # yearn
    yusdp3crv = safe.contract('0xC4dAf3b5e2A9e93861c3FBDd25f1e943B8D87417')

    # pull amount of tokens locked
    cdp_parameters = unit_cdp_viewer.getCollateralParameters(xsushi, safe.address)
    xsushi_locked = cdp_parameters["cdp"]["collateral"]

    liquidation_price = unit_cdp_manager.liquidationPrice_q112(xsushi, safe.account) / unit_cdp_manager.Q112()
    print("Liquidation price:", liquidation_price)

    # check that owner and tokens are correct
    assert xsushi_locked > 0

    yusdp3crv.withdrawAll()
    # withdraw curve
    lp_balance = curve_usdp_lp.balanceOf(safe.address)
    usdp_index = 0
    min_amount = curve_usdp_pool.calc_withdraw_one_coin(lp_balance, usdp_index)
    curve_usdp_pool.remove_liquidity_one_coin(lp_balance, 0, min_amount * 0.99) # 1% slippage is okay

    usdp.approve(unit_vault, usdp.balanceOf(safe.address))
    unit_cdp_manager.exit(xsushi, xsushi_locked, usdp.balanceOf(safe.address))

    assert xsushi_locked == xsushi.balanceOf(safe.address)

    safe_tx = safe.multisend_from_receipts()
    safe.preview(safe_tx, call_trace=True)
    safe.post_transaction(safe_tx)


def send_slp():
    '''
        Send SLP KP3R-ETH to burner address
    '''
    safe = ApeSafe("0x0D5Dc686d0a2ABBfDaFDFb4D0533E886517d4E83")

    assert safe.address == THE_KEEP3R

    burner = "0x5f0845101857d2A91627478e302357860b1598a1"
    sushi_chief = safe.contract("0xc2EdaD668740f1aA35E4D8f227fB8E17dcA888Cd")
    slp = safe.contract("0xaf988afF99d3d0cb870812C325C588D8D8CB7De8")

    _pid = 58 # KP3R-ETH
    amount = 700 * 1e18
    sushi_chief.withdraw(_pid, amount)

    assert slp.balanceOf(safe.address) >= amount

    slp.transfer(burner, amount)

    assert slp.balanceOf(burner) == amount

    safe_tx = safe.multisend_from_receipts()
    safe.preview(safe_tx, call_trace=True)
    safe.post_transaction(safe_tx)


def set_ens():
    '''
        Add ens thekeep3r.eth for multisig address
    '''
    safe = ApeSafe("0x0D5Dc686d0a2ABBfDaFDFb4D0533E886517d4E83")

    assert safe.address == THE_KEEP3R

    ens = safe.contract("0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e")
    resolver = safe.contract("0x4976fb03C32e5B8cfe2b6cCB31c09Ba78EBaBa41")

    ens.setOwner(web3.ens.namehash("thekeep3r.eth"), safe.address)
    ens.setResolver(web3.ens.namehash("thekeep3r.eth"), resolver)
    resolver.setAddr(web3.ens.namehash("thekeep3r.eth"), safe.address)

    assert web3.ens.resolve("thekeep3r.eth") == safe.address
    assert web3.ens.resolve("thekeep3r.eth") == THE_KEEP3R

    safe_tx = safe.multisend_from_receipts()
    safe.preview(safe_tx, call_trace=True)
    safe.post_transaction(safe_tx)


def slash_keep3r():
    '''
        Slash keep3r and pull his bond
    '''
    safe = ApeSafe(web3.ens.resolve("thekeep3r.eth"))

    assert safe.address == THE_KEEP3R

    keep3r = safe.contract("0x1cEB5cB57C4D4E2b2433641b95Dd330A33185A44")
    abuser = "0x6352f8C749954c9Df198cf72976E48994A77cCE2"

    before = keep3r.balanceOf(safe.address)
    amount = keep3r.bonds(abuser, keep3r)

    # blacklist and slash, blacklist is irreversible
    keep3r.revoke(abuser)

    assert before + amount == keep3r.balanceOf(safe.address)

    safe_tx = safe.multisend_from_receipts()
    safe.preview(safe_tx, call_trace=True)
    safe.post_transaction(safe_tx)
