/**
 * Solana Payment — Build and send USDC SPL token transfers via Phantom.
 *
 * Flow:
 *   1. Get payment details from backend (amount, recipient, token mint, rpc_url)
 *   2. Build SPL Token transfer instruction
 *   3. User approves in Phantom → signAndSendTransaction
 *   4. Return tx signature for backend verification
 *
 * Supports both mainnet and devnet — RPC URL comes from backend config.
 */

import {
    Connection,
    PublicKey,
    Transaction,
    type TransactionSignature,
} from '@solana/web3.js';
import {
    createTransferInstruction,
    getAssociatedTokenAddress,
    createAssociatedTokenAccountInstruction,
    getAccount,
} from '@solana/spl-token';

/** USDC has 6 decimal places */
const USDC_DECIMALS = 6;

interface PhantomProvider {
    isPhantom: boolean;
    publicKey: PublicKey | null;
    isConnected: boolean;
    signAndSendTransaction(
        transaction: Transaction,
        options?: { skipPreflight?: boolean }
    ): Promise<{ signature: TransactionSignature }>;
    connect(): Promise<{ publicKey: PublicKey }>;
}

function getPhantom(): PhantomProvider {
    const provider = (window as any)?.phantom?.solana;
    if (!provider?.isPhantom) {
        throw new Error('Phantom wallet not found. Please install it from phantom.app');
    }
    return provider as PhantomProvider;
}

/**
 * Send USDC to the treasury wallet via Phantom.
 *
 * @param recipientAddress  Treasury wallet address (base58)
 * @param amountUsdc        Amount in USDC (e.g. 29.0)
 * @param tokenMint         USDC mint address (base58)
 * @param rpcUrl            Solana RPC URL (devnet or mainnet — from backend)
 * @returns Transaction signature string
 */
export async function sendUsdcPayment(
    recipientAddress: string,
    amountUsdc: number,
    tokenMint: string,
    rpcUrl: string,
): Promise<string> {
    const phantom = getPhantom();

    // Ensure connected
    if (!phantom.isConnected || !phantom.publicKey) {
        await phantom.connect();
    }

    const senderPubkey = phantom.publicKey!;
    const recipientPubkey = new PublicKey(recipientAddress);
    const mintPubkey = new PublicKey(tokenMint);
    const connection = new Connection(rpcUrl, 'confirmed');

    // Convert USDC to raw amount (6 decimals)
    const rawAmount = BigInt(Math.round(amountUsdc * 10 ** USDC_DECIMALS));

    // Get Associated Token Accounts (ATAs)
    const senderAta = await getAssociatedTokenAddress(mintPubkey, senderPubkey);
    const recipientAta = await getAssociatedTokenAddress(mintPubkey, recipientPubkey);

    // Build transaction
    const tx = new Transaction();

    // Check if recipient ATA exists; if not, create it (sender pays)
    try {
        await getAccount(connection, recipientAta);
    } catch {
        // ATA doesn't exist — add creation instruction
        tx.add(
            createAssociatedTokenAccountInstruction(
                senderPubkey,    // payer
                recipientAta,    // ATA to create
                recipientPubkey, // owner
                mintPubkey,      // mint
            )
        );
    }

    // Add SPL transfer instruction
    tx.add(
        createTransferInstruction(
            senderAta,      // source ATA
            recipientAta,   // destination ATA
            senderPubkey,   // owner/authority
            rawAmount,      // amount in raw units
        )
    );

    // Get recent blockhash
    const { blockhash } = await connection.getLatestBlockhash('confirmed');
    tx.recentBlockhash = blockhash;
    tx.feePayer = senderPubkey;

    // Sign and send via Phantom
    const { signature } = await phantom.signAndSendTransaction(tx, {
        skipPreflight: false,
    });

    // Wait for confirmation
    await connection.confirmTransaction(signature, 'confirmed');

    return signature;
}
