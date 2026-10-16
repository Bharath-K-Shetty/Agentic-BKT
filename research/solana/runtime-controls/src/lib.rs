//! Authored experimental controls, not production findings or copied upstream PoCs.
#![allow(unexpected_cfgs)]
use solana_program::{
    account_info::{next_account_info, AccountInfo},
    entrypoint,
    entrypoint::ProgramResult,
    instruction::Instruction,
    msg,
    program::{get_return_data, invoke, set_return_data},
    program_error::ProgramError,
    pubkey::Pubkey,
};

entrypoint!(process);
pub fn process(program_id: &Pubkey, accounts: &[AccountInfo], data: &[u8]) -> ProgramResult {
    let mut iter = accounts.iter();
    match data.first().copied() {
        // Writer used for legally constructing attacker-controlled account bytes.
        Some(0) => {
            let target = next_account_info(&mut iter)?;
            if !target.is_signer {
                return Err(ProgramError::MissingRequiredSignature);
            }
            if target.owner != program_id {
                return Err(ProgramError::IllegalOwner);
            }
            // Trusted records require a fixture admin; outsiders cannot simply
            // choose this owner and initialize arbitrary trusted data themselves.
            if *program_id
                == solana_program::pubkey!("6kfnBaroMT6L4YwBdFotwuuK3c7AaWCiwWzJDyeJNNi6")
            {
                let admin = next_account_info(&mut iter)?;
                if !admin.is_signer
                    || *admin.key
                        != solana_program::pubkey!("GDz12fWMJsBvg2381UmjrRG4w8b9BFXcxhgGVrD5EsAV")
                {
                    return Err(ProgramError::MissingRequiredSignature);
                }
            }
            target.try_borrow_mut_data()?.copy_from_slice(&data[1..]);
        }
        // Same balance assertion, with and without account-producer verification.
        Some(mode @ (1 | 2)) => {
            let record = next_account_info(&mut iter)?;
            let authority = next_account_info(&mut iter)?;
            let expected_owner = next_account_info(&mut iter)?;
            if !authority.is_signer {
                return Err(ProgramError::MissingRequiredSignature);
            }
            if mode == 2 && record.owner != expected_owner.key {
                return Err(ProgramError::IllegalOwner);
            }
            let bytes = record.try_borrow_data()?;
            if bytes.len() != 40 || bytes[..32] != authority.key.to_bytes() {
                return Err(ProgramError::InvalidAccountData);
            }
            let balance = u64::from_le_bytes(bytes[32..40].try_into().unwrap());
            if balance != 999 {
                return Err(ProgramError::InvalidAccountData);
            }
            msg!("CONTROL: accepted fabricated balance");
        }
        Some(3) => set_return_data(&7u64.to_le_bytes()),
        Some(4) => set_return_data(&999u64.to_le_bytes()),
        // Local model of delayed Return<T>::get(), not an Anchor reproduction.
        Some(mode @ (5 | 6)) => {
            let trusted = next_account_info(&mut iter)?;
            let untrusted = next_account_info(&mut iter)?;
            invoke(
                &Instruction::new_with_bytes(*trusted.key, &[3], vec![]),
                &[trusted.clone()],
            )?;
            invoke(
                &Instruction::new_with_bytes(*untrusted.key, &[4], vec![]),
                &[untrusted.clone()],
            )?;
            let (producer, value) = get_return_data().ok_or(ProgramError::InvalidAccountData)?;
            if mode == 6 && producer != *trusted.key {
                return Err(ProgramError::IncorrectProgramId);
            }
            if value != 999u64.to_le_bytes() {
                return Err(ProgramError::InvalidAccountData);
            }
            msg!("CONTROL: accepted substituted return data");
        }
        _ => return Err(ProgramError::InvalidInstructionData),
    }
    Ok(())
}
