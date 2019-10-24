from tests.network.nano_node.conftest import HTTPReplay


DATA = [
    # Account not synced
    HTTPReplay(
        {
            "action": "account_history",
            "account": "xrb_3rropjiqfxpmrrkooej4qtmm1pueu36f9ghinpho4esfdor8785a455d16nf",
            "count": 500,
            "raw": True,
            "reverse": True
        },
        {
            "account": "xrb_3rropjiqfxpmrrkooej4qtmm1pueu36f9ghinpho4esfdor8785a455d16nf",
            "history": [
                {
                    "account": "xrb_17umjjw1rroj7hgg54zzurcd5cbtjr85u97hiss37i9bgj643xrozgxpw8rc",
                    "amount": "1000000000000000000000000",
                    "hash": "088EE46429CA936F76C4EAA20B97F6D33E5D872971433EE0C1311BCB98764456",
                    "local_timestamp": "0",
                    "opened": "xrb_3rropjiqfxpmrrkooej4qtmm1pueu36f9ghinpho4esfdor8785a455d16nf",
                    "representative": "xrb_1hza3f7wiiqa7ig3jczyxj5yo86yegcmqk3criaz838j91sxcckpfhbhhra1",
                    "signature": "63922389430E2775EACDCF811AC6DF4E008BDB9CD821420AB5CE933DB9B6C3BC5FCACFB2A513E9514505DF6BCC3F4E2FB16F5CD4E8957C77D541717484F1730A",
                    "source": "E749404912F8C239E2F413B7C604E5732F428C9DEC4BA649AEBB54AC964EBFA4",
                    "timestamp": None,
                    "type": "open",
                    "work": "d7352e6f3fffd5c0"
                },
                {
                    "hash": "13552AC3928E93B5C6C215F61879358E248D4A5246B8B3D1EEC5A566EDCEE077",
                    "local_timestamp": "0",
                    "previous": "088EE46429CA936F76C4EAA20B97F6D33E5D872971433EE0C1311BCB98764456",
                    "representative": "xrb_3rropjiqfxpmrrkooej4qtmm1pueu36f9ghinpho4esfdor8785a455d16nf",
                    "signature": "491F965A1B61E66C62B5AA39F0F9EFA0782ADB7304CB73F8ACB350FBDC1480A48E08A2A825B977E686A844D8994085C1961B86B28BB98536EC4A84873A9EF40B",
                    "timestamp": "1522284853935",
                    "type": "change",
                    "work": "e93328ea63ac480e"
                },
                {
                    "account": "xrb_3x7cjioqahgs5ppheys6prpqtb4rdknked83chf97bot1unrbdkaux37t31b",
                    "amount": "415589316951048370157256704",
                    "hash": "D6E1921FA6B341EE1D3EC36F31AF3B7B73EE17F82CA80B76002EDBA30B82B447",
                    "local_timestamp": "0",
                    "previous": "13552AC3928E93B5C6C215F61879358E248D4A5246B8B3D1EEC5A566EDCEE077",
                    # This signature is invalid and will stall the sync
                    # process
                    "signature": "E34C6CAD6192AE47BFD3EEEA2C2CD1ED6EC03CD8027588A3C28173F85B0B21DAC04377E0BD82901CFD266ECDFA26D4B4B8B86E0645C530244A1D683033249309",
                    "source": "786E621F133DDC9DA97808CEF006499845D3ED660C0630BCC7B21FE313F869F8",
                    "timestamp": "1522295633711",
                    "type": "receive",
                    "work": "eef4678129108060"
                },
                {
                    "account": "xrb_1qckwc5o3obkrwbet4amnkya113xq77qpaknsmiq9hwq31tmd5bpyo7sepsw",
                    "amount": "1000000000000000000000000000",
                    "hash": "94EA9E9DC69B7634560B56B21EF47A04C7ADC7CF80BB911267A9D7C824EEB83C",
                    "local_timestamp": "0",
                    "previous": "D6E1921FA6B341EE1D3EC36F31AF3B7B73EE17F82CA80B76002EDBA30B82B447",
                    "signature": "F83E767ACB079BA527138C63A18540DEA939FDA63C3CA545AF80CD5B6A8974F71891C5E41769FBC157F4896956E9BCC5D57AEB253D10FF46FE9CA7F48BBCAF06",
                    "source": "548E61BAF6CF07E418324D2D08DAB0FC710681837E94C30242E14C97169AB529",
                    "timestamp": "1523535231236",
                    "type": "receive",
                    "work": "e121b2d042a5056d"
                },
                {
                    "account": "xrb_1xjmoz4pkewycoaoqmfdncht1q4uso5yeiq5z1c1ict1jtz3qbrbddyoze35",
                    "amount": "1000000000000000000000000",
                    "balance": "1415589316951048370157256704",
                    "destination": "xrb_1xjmoz4pkewycoaoqmfdncht1q4uso5yeiq5z1c1ict1jtz3qbrbddyoze35",
                    "hash": "BCDEF4D74B0D93231B1C6CFDBA21DC189CFF4D69BE8FAC07278968FE0BC09FFC",
                    "local_timestamp": "0",
                    "previous": "94EA9E9DC69B7634560B56B21EF47A04C7ADC7CF80BB911267A9D7C824EEB83C",
                    "signature": "E6C6C4AB8C180C8EC89DB2F579374486356C39C2967BB4A5F4EDD512C00DE40AD932D98053036288FAA6604817E0CE74BA4FE5D4835D76732BA0629199D64C04",
                    "timestamp": "1523535582222",
                    "type": "send",
                    "work": "65b3c6d0972889be"
                },
            ]
        }
    ),
    # Sync account (head = 94EA...)
    HTTPReplay(
        {
            "action": "account_history",
            "account": "xrb_3rropjiqfxpmrrkooej4qtmm1pueu36f9ghinpho4esfdor8785a455d16nf",
            "count": 500,
            "reverse": True,
            "raw": True,
            "head": "13552AC3928E93B5C6C215F61879358E248D4A5246B8B3D1EEC5A566EDCEE077"
        },
        {
            "account": "xrb_3rropjiqfxpmrrkooej4qtmm1pueu36f9ghinpho4esfdor8785a455d16nf",
            "history": [
                {
                    "hash": "13552AC3928E93B5C6C215F61879358E248D4A5246B8B3D1EEC5A566EDCEE077",
                    "local_timestamp": "0",
                    "previous": "088EE46429CA936F76C4EAA20B97F6D33E5D872971433EE0C1311BCB98764456",
                    "representative": "xrb_3rropjiqfxpmrrkooej4qtmm1pueu36f9ghinpho4esfdor8785a455d16nf",
                    "signature": "491F965A1B61E66C62B5AA39F0F9EFA0782ADB7304CB73F8ACB350FBDC1480A48E08A2A825B977E686A844D8994085C1961B86B28BB98536EC4A84873A9EF40B",
                    "timestamp": "1522284853935",
                    "type": "change",
                    "work": "e93328ea63ac480e"
                },
                {
                    "account": "xrb_3x7cjioqahgs5ppheys6prpqtb4rdknked83chf97bot1unrbdkaux37t31b",
                    "amount": "415589316951048370157256704",
                    "hash": "D6E1921FA6B341EE1D3EC36F31AF3B7B73EE17F82CA80B76002EDBA30B82B447",
                    "local_timestamp": "0",
                    "previous": "13552AC3928E93B5C6C215F61879358E248D4A5246B8B3D1EEC5A566EDCEE077",
                    # This signature is invalid and will stall the sync
                    # process
                    "signature": "E34C6CAD6192AE47BFD3EEEA2C2CD1ED6EC03CD8027588A3C28173F85B0B21DAC04377E0BD82901CFD266ECDFA26D4B4B8B86E0645C530244A1D683033249309",
                    "source": "786E621F133DDC9DA97808CEF006499845D3ED660C0630BCC7B21FE313F869F8",
                    "timestamp": "1522295633711",
                    "type": "receive",
                    "work": "eef4678129108060"
                },
                {
                    "account": "xrb_1qckwc5o3obkrwbet4amnkya113xq77qpaknsmiq9hwq31tmd5bpyo7sepsw",
                    "amount": "1000000000000000000000000000",
                    "hash": "94EA9E9DC69B7634560B56B21EF47A04C7ADC7CF80BB911267A9D7C824EEB83C",
                    "local_timestamp": "0",
                    "previous": "D6E1921FA6B341EE1D3EC36F31AF3B7B73EE17F82CA80B76002EDBA30B82B447",
                    "signature": "F83E767ACB079BA527138C63A18540DEA939FDA63C3CA545AF80CD5B6A8974F71891C5E41769FBC157F4896956E9BCC5D57AEB253D10FF46FE9CA7F48BBCAF06",
                    "source": "548E61BAF6CF07E418324D2D08DAB0FC710681837E94C30242E14C97169AB529",
                    "timestamp": "1523535231236",
                    "type": "receive",
                    "work": "e121b2d042a5056d"
                },
                {
                    "account": "xrb_1xjmoz4pkewycoaoqmfdncht1q4uso5yeiq5z1c1ict1jtz3qbrbddyoze35",
                    "amount": "1000000000000000000000000",
                    "balance": "1415589316951048370157256704",
                    "destination": "xrb_1xjmoz4pkewycoaoqmfdncht1q4uso5yeiq5z1c1ict1jtz3qbrbddyoze35",
                    "hash": "BCDEF4D74B0D93231B1C6CFDBA21DC189CFF4D69BE8FAC07278968FE0BC09FFC",
                    "local_timestamp": "0",
                    "previous": "94EA9E9DC69B7634560B56B21EF47A04C7ADC7CF80BB911267A9D7C824EEB83C",
                    "signature": "E6C6C4AB8C180C8EC89DB2F579374486356C39C2967BB4A5F4EDD512C00DE40AD932D98053036288FAA6604817E0CE74BA4FE5D4835D76732BA0629199D64C04",
                    "timestamp": "1523535582222",
                    "type": "send",
                    "work": "65b3c6d0972889be"
                }
            ]
        }
    ),
    # blocks_info for actual blocks
    HTTPReplay(
        {
            "action": "blocks_info",
            "hashes": [
                "088EE46429CA936F76C4EAA20B97F6D33E5D872971433EE0C1311BCB98764456",
                "D6E1921FA6B341EE1D3EC36F31AF3B7B73EE17F82CA80B76002EDBA30B82B447",
                "94EA9E9DC69B7634560B56B21EF47A04C7ADC7CF80BB911267A9D7C824EEB83C",
                "BCDEF4D74B0D93231B1C6CFDBA21DC189CFF4D69BE8FAC07278968FE0BC09FFC"
            ]
        },
        {
            "blocks": {
                "088EE46429CA936F76C4EAA20B97F6D33E5D872971433EE0C1311BCB98764456": {
                    "amount": "1000000000000000000000000",
                    "balance": "1000000000000000000000000",
                    "block_account": "xrb_3rropjiqfxpmrrkooej4qtmm1pueu36f9ghinpho4esfdor8785a455d16nf",
                    "contents": "{\n    \"type\": \"open\",\n    \"source\": \"E749404912F8C239E2F413B7C604E5732F428C9DEC4BA649AEBB54AC964EBFA4\",\n    \"representative\": \"xrb_1hza3f7wiiqa7ig3jczyxj5yo86yegcmqk3criaz838j91sxcckpfhbhhra1\",\n    \"account\": \"xrb_3rropjiqfxpmrrkooej4qtmm1pueu36f9ghinpho4esfdor8785a455d16nf\",\n    \"work\": \"d7352e6f3fffd5c0\",\n    \"signature\": \"63922389430E2775EACDCF811AC6DF4E008BDB9CD821420AB5CE933DB9B6C3BC5FCACFB2A513E9514505DF6BCC3F4E2FB16F5CD4E8957C77D541717484F1730A\"\n}\n",
                    "height": "1",
                    "local_timestamp": "0",
                    "timestamp": None
                },
                "94EA9E9DC69B7634560B56B21EF47A04C7ADC7CF80BB911267A9D7C824EEB83C": {
                    "amount": "1000000000000000000000000000",
                    "balance": "1416589316951048370157256704",
                    "block_account": "xrb_3rropjiqfxpmrrkooej4qtmm1pueu36f9ghinpho4esfdor8785a455d16nf",
                    "contents": "{\n    \"type\": \"receive\",\n    \"previous\": \"D6E1921FA6B341EE1D3EC36F31AF3B7B73EE17F82CA80B76002EDBA30B82B447\",\n    \"source\": \"548E61BAF6CF07E418324D2D08DAB0FC710681837E94C30242E14C97169AB529\",\n    \"work\": \"e121b2d042a5056d\",\n    \"signature\": \"F83E767ACB079BA527138C63A18540DEA939FDA63C3CA545AF80CD5B6A8974F71891C5E41769FBC157F4896956E9BCC5D57AEB253D10FF46FE9CA7F48BBCAF06\"\n}\n",
                    "height": "4",
                    "local_timestamp": "0",
                    "timestamp": "1523535231236"
                },
                "BCDEF4D74B0D93231B1C6CFDBA21DC189CFF4D69BE8FAC07278968FE0BC09FFC": {
                    "amount": "1000000000000000000000000",
                    "balance": "1415589316951048370157256704",
                    "block_account": "xrb_3rropjiqfxpmrrkooej4qtmm1pueu36f9ghinpho4esfdor8785a455d16nf",
                    "contents": "{\n    \"type\": \"send\",\n    \"previous\": \"94EA9E9DC69B7634560B56B21EF47A04C7ADC7CF80BB911267A9D7C824EEB83C\",\n    \"destination\": \"xrb_1xjmoz4pkewycoaoqmfdncht1q4uso5yeiq5z1c1ict1jtz3qbrbddyoze35\",\n    \"balance\": \"000000000492F2B2A3A7D8ECE8000000\",\n    \"work\": \"65b3c6d0972889be\",\n    \"signature\": \"E6C6C4AB8C180C8EC89DB2F579374486356C39C2967BB4A5F4EDD512C00DE40AD932D98053036288FAA6604817E0CE74BA4FE5D4835D76732BA0629199D64C04\"\n}\n",
                    "height": "5",
                    "local_timestamp": "0",
                    "timestamp": "1523535582222"
                },
                "D6E1921FA6B341EE1D3EC36F31AF3B7B73EE17F82CA80B76002EDBA30B82B447": {
                    "amount": "415589316951048370157256704",
                    "balance": "416589316951048370157256704",
                    "block_account": "xrb_3rropjiqfxpmrrkooej4qtmm1pueu36f9ghinpho4esfdor8785a455d16nf",
                    "contents": "{\n    \"type\": \"receive\",\n    \"previous\": \"13552AC3928E93B5C6C215F61879358E248D4A5246B8B3D1EEC5A566EDCEE077\",\n    \"source\": \"786E621F133DDC9DA97808CEF006499845D3ED660C0630BCC7B21FE313F869F8\",\n    \"work\": \"eef4678129108060\",\n    \"signature\": \"F34C6CAD6192AE47BFD3EEEA2C2CD1ED6EC03CD8027588A3C28173F85B0B21DAC04377E0BD82901CFD266ECDFA26D4B4B8B86E0645C530244A1D683033249309\"\n}\n",
                    "height": "3",
                    "local_timestamp": "0",
                    "timestamp": "1522295633711"
                }
            }
        }
    ),
    # blocks_info for link blocks
    HTTPReplay(
        {
            "action": "blocks_info",
            "hashes": [
                "E749404912F8C239E2F413B7C604E5732F428C9DEC4BA649AEBB54AC964EBFA4",
            ]
        },
        {
            "blocks": {
                "E749404912F8C239E2F413B7C604E5732F428C9DEC4BA649AEBB54AC964EBFA4": {
                    "amount": "1000000000000000000000000",
                    "balance": "5000000000000000000000000",
                    "block_account": "xrb_17umjjw1rroj7hgg54zzurcd5cbtjr85u97hiss37i9bgj643xrozgxpw8rc",
                    "contents": "{\n    \"type\": \"send\",\n    \"previous\": \"E3879B55C0BB2A95CB65161400A52930A8169F9184559136D7482532DD4B510B\",\n    \"destination\": \"xrb_3rropjiqfxpmrrkooej4qtmm1pueu36f9ghinpho4esfdor8785a455d16nf\",\n    \"balance\": \"00000000000422CA8B0A00A425000000\",\n    \"work\": \"268f7d8ee00a8f09\",\n    \"signature\": \"F883EF6B0EBAF0CDB767AC7D2FE8D61E1E392E9BC2601E6BE5852DFB1FF831BF06CA8C25675C682DACE6D263E8CF2CBBAEA39D8E21CD3A2176B734AAFFFA6301\"\n}\n",
                    "height": "15",
                    "local_timestamp": "1551151144"
                }
            }
        }
    ),
    # accounts_pending
    HTTPReplay(
        {
            "action": "accounts_pending",
            "accounts": [
                "xrb_3rropjiqfxpmrrkooej4qtmm1pueu36f9ghinpho4esfdor8785a455d16nf"
            ],
            "threshold": "100000000000000000000000000",
            "source": True
        },
        {
            "blocks": {
                "xrb_3rropjiqfxpmrrkooej4qtmm1pueu36f9ghinpho4esfdor8785a455d16nf": ""
            }
        }
    )
]
