package org.allma.backup;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

/** A typed boundary avoids ambiguous Cipher.init overloads through PyJNIus. */
public final class BackupCipher {
    private BackupCipher() {}

    public static byte[] crypt(int mode, byte[] key, byte[] nonce, byte[] data, byte[] aad)
            throws Exception {
        if ((mode != Cipher.ENCRYPT_MODE && mode != Cipher.DECRYPT_MODE)
                || key.length != 32 || nonce.length != 12) {
            throw new IllegalArgumentException("Invalid backup cipher parameters");
        }
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(mode, new SecretKeySpec(key, "AES"), new GCMParameterSpec(128, nonce));
        cipher.updateAAD(aad);
        return cipher.doFinal(data);
    }
}
